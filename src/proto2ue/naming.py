"""Name resolution utilities used across proto2ue generators."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from importlib import resources
from typing import Dict, Iterable, Mapping, MutableMapping, Optional, Sequence, Set

_DEFAULT_RESOURCE_PACKAGE = "proto2ue.data"
_DEFAULT_CONFIG_RESOURCE = "naming_config.json"
_ENV_CONFIG_PATH = "PROTO2UE_NAMING_CONFIG"


def _load_json_from_path(path: str) -> Mapping[str, object]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_default_json() -> Mapping[str, object]:
    data_path = resources.files(_DEFAULT_RESOURCE_PACKAGE) / _DEFAULT_CONFIG_RESOURCE
    with data_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@dataclass(frozen=True, slots=True)
class NamingRules:
    """Configuration describing how UE names are assigned."""

    reserved_symbols: frozenset[str]
    overrides: Mapping[str, str]
    collision_suffix: str = "Proto"

    def with_overrides(self, overrides: Mapping[str, str]) -> "NamingRules":
        merged: Dict[str, str] = dict(self.overrides)
        merged.update({key: value for key, value in overrides.items() if value})
        return NamingRules(
            reserved_symbols=self.reserved_symbols,
            overrides=merged,
            collision_suffix=self.collision_suffix,
        )


def load_naming_rules(path: Optional[str] = None) -> NamingRules:
    """Load :class:`NamingRules` from *path* or bundled defaults.

    If *path* is ``None`` the environment variable ``PROTO2UE_NAMING_CONFIG`` is
    consulted before falling back to the packaged defaults.
    """

    config_path = path or os.environ.get(_ENV_CONFIG_PATH)
    if config_path:
        data = _load_json_from_path(config_path)
    else:
        data = _load_default_json()

    reserved = data.get("reserved_symbols", [])
    if not isinstance(reserved, Sequence):
        raise TypeError("'reserved_symbols' must be a sequence of strings")
    reserved_set: Set[str] = set()
    for entry in reserved:
        if not isinstance(entry, str):
            raise TypeError("Reserved symbol entries must be strings")
        stripped = entry.strip()
        if stripped:
            reserved_set.add(stripped)

    overrides_raw = data.get("overrides", {})
    if not isinstance(overrides_raw, Mapping):
        raise TypeError("'overrides' must be a mapping of proto names to UE names")
    overrides: Dict[str, str] = {}
    for key, value in overrides_raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise TypeError("Override keys and values must be strings")
        key_stripped = key.strip()
        value_stripped = value.strip()
        if key_stripped and value_stripped:
            overrides[key_stripped] = value_stripped

    collision_suffix = data.get("collision_suffix", "Proto")
    if not isinstance(collision_suffix, str) or not collision_suffix:
        collision_suffix = "Proto"

    return NamingRules(
        reserved_symbols=frozenset(reserved_set),
        overrides=overrides,
        collision_suffix=collision_suffix,
    )


class NameResolver:
    """Resolve UE type names from protobuf full names with collision handling."""

    def __init__(
        self,
        rules: NamingRules,
        *,
        additional_reserved: Optional[Iterable[str]] = None,
    ) -> None:
        self._rules = rules
        self._symbols: MutableMapping[str, str] = {}
        reserved: Set[str] = set(rules.reserved_symbols)
        if additional_reserved is not None:
            for entry in additional_reserved:
                if not isinstance(entry, str):
                    continue
                stripped = entry.strip()
                if stripped:
                    reserved.add(stripped)
        self._reserved = reserved

    def register(self, full_name: str, prefix: str, suffix: str) -> str:
        """Register *full_name* and return the UE type name."""

        if full_name in self._symbols:
            return self._symbols[full_name]

        override = self._rules.overrides.get(full_name)
        if override:
            if override in self._reserved:
                raise ValueError(
                    f"Override '{override}' for type '{full_name}' conflicts with an existing UE symbol"
                )
            self._reserved.add(override)
            self._symbols[full_name] = override
            return override

        candidate = self._make_unique(prefix, suffix)
        self._symbols[full_name] = candidate
        return candidate

    def lookup(self, full_name: str) -> str:
        """Return the resolved UE name for *full_name*."""

        try:
            return self._symbols[full_name]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise KeyError(f"Type '{full_name}' has not been registered") from exc

    def _make_unique(self, prefix: str, suffix: str) -> str:
        candidate = prefix + suffix
        if self._is_available(candidate):
            self._reserved.add(candidate)
            return candidate

        base_suffix = f"{self._rules.collision_suffix}{suffix}" if suffix else self._rules.collision_suffix
        attempt = 1
        while True:
            adjusted_suffix = base_suffix if attempt == 1 else f"{base_suffix}{attempt - 1}"
            candidate = prefix + adjusted_suffix
            if self._is_available(candidate):
                self._reserved.add(candidate)
                return candidate
            attempt += 1

    def _is_available(self, name: str) -> bool:
        return name not in self._reserved


__all__ = ["NameResolver", "NamingRules", "load_naming_rules"]
