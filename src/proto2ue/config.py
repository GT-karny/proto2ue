"""Configuration helpers for proto2ue code generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

_TRUE_VALUES = {"true", "1", "yes", "on"}
_FALSE_VALUES = {"false", "0", "no", "off"}

DEFAULT_RESERVED_IDENTIFIERS: Tuple[str, ...] = (
    "FVector",
    "FVector2D",
    "FVector3d",
    "FVector4",
    "FVector4d",
    "EVector",
    "EVector2D",
    "EVector3d",
    "EVector4",
    "EVector4d",
    "EVectorState",
)


def _parse_parameter_string(parameter: str | None) -> Dict[str, str]:
    if not parameter:
        return {}

    entries = parameter.replace(";", ",").split(",")
    result: Dict[str, str] = {}
    for entry in entries:
        piece = entry.strip()
        if not piece:
            continue
        if "=" in piece:
            key, value = piece.split("=", 1)
            result[key.strip().lower()] = value.strip()
        else:
            result[piece.lower()] = "true"
    return result


def _to_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _TRUE_VALUES:
            return True
        if lowered in _FALSE_VALUES:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return None


def _split_config_tokens(raw: str | None) -> List[str]:
    if not raw:
        return []
    normalized = raw
    for separator in ("|", ";"):
        normalized = normalized.replace(separator, ",")
    return [piece.strip() for piece in normalized.split(",") if piece.strip()]


def _load_identifier_file(path_value: str | None) -> List[str]:
    if not path_value:
        return []
    path = Path(path_value).expanduser()
    content = path.read_text(encoding="utf-8")
    entries: List[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entries.append(stripped)
    return entries


def _parse_rename_entries(entries: Iterable[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for entry in entries:
        if not entry:
            continue
        if ":" not in entry:
            raise ValueError(
                "Rename override entries must use the form 'full.proto.Name:UEName'"
            )
        proto_name, ue_name = entry.split(":", 1)
        proto_key = proto_name.strip()
        ue_value = ue_name.strip()
        if not proto_key or not ue_value:
            raise ValueError(
                "Rename override entries must include both a proto name and a UE name"
            )
        mapping[proto_key] = ue_value
    return mapping


@dataclass(slots=True)
class GeneratorConfig:
    """Runtime configuration for proto2ue generation."""

    convert_unsigned_to_blueprint: bool = False
    reserved_identifiers: Tuple[str, ...] = DEFAULT_RESERVED_IDENTIFIERS
    rename_overrides: Dict[str, str] = field(default_factory=dict)
    include_package_in_names: bool = True

    @classmethod
    def from_parameter_string(cls, parameter: str | None) -> "GeneratorConfig":
        overrides = _parse_parameter_string(parameter)

        convert_flag = overrides.get("convert_unsigned_for_blueprint")
        if convert_flag is None:
            convert_flag = overrides.get("convert_unsigned_to_blueprint")
        convert_value = _to_bool(convert_flag)

        reserved_entries: List[str]
        reserved_entries = list(DEFAULT_RESERVED_IDENTIFIERS)
        reserved_override = overrides.get("reserved_identifiers")
        if reserved_override:
            reserved_entries = _split_config_tokens(reserved_override)
        extra_reserved = overrides.get("extra_reserved_identifiers")
        if extra_reserved:
            reserved_entries.extend(_split_config_tokens(extra_reserved))
        reserved_file = overrides.get("reserved_identifiers_file")
        if reserved_file:
            reserved_entries.extend(_load_identifier_file(reserved_file))

        unique_reserved = tuple(dict.fromkeys(entry for entry in reserved_entries if entry))

        rename_entries: List[str] = []
        rename_override = overrides.get("rename_overrides")
        if rename_override:
            rename_entries.extend(_split_config_tokens(rename_override))
        rename_file = overrides.get("rename_overrides_file")
        if rename_file:
            rename_entries.extend(_load_identifier_file(rename_file))
        rename_overrides = _parse_rename_entries(rename_entries)

        include_package_flag = overrides.get("include_package_in_names")
        include_package_value = _to_bool(include_package_flag)

        return cls(
            convert_unsigned_to_blueprint=convert_value if convert_value is not None else False,
            reserved_identifiers=unique_reserved,
            rename_overrides=rename_overrides,
            include_package_in_names=
                include_package_value if include_package_value is not None else True,
        )


__all__ = ["GeneratorConfig", "DEFAULT_RESERVED_IDENTIFIERS"]

