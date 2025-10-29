"""Configuration helpers for proto2ue code generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

_TRUE_VALUES = {"true", "1", "yes", "on"}
_FALSE_VALUES = {"false", "0", "no", "off"}


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


@dataclass(slots=True)
class GeneratorConfig:
    """Runtime configuration for proto2ue generation."""

    convert_unsigned_to_blueprint: bool = False

    @classmethod
    def from_parameter_string(cls, parameter: str | None) -> "GeneratorConfig":
        overrides = _parse_parameter_string(parameter)
        convert_flag = overrides.get("convert_unsigned_for_blueprint")
        if convert_flag is None:
            convert_flag = overrides.get("convert_unsigned_to_blueprint")
        value = _to_bool(convert_flag)
        return cls(convert_unsigned_to_blueprint=value if value is not None else False)


__all__ = ["GeneratorConfig"]

