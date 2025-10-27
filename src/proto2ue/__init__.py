"""proto2ue package initialization."""

from __future__ import annotations

from . import model

__all__ = [
    "DescriptorLoader",
    "OptionContext",
    "OptionValidator",
    "model",
    "TypeMapper",
    "UEEnum",
    "UEEnumValue",
    "UEField",
    "UEMessage",
    "UEOneofCase",
    "UEOneofWrapper",
    "UEProtoFile",
]


def __getattr__(name: str):
    if name in {"DescriptorLoader", "OptionContext", "OptionValidator"}:
        from .descriptor_loader import DescriptorLoader, OptionContext, OptionValidator

        mapping = {
            "DescriptorLoader": DescriptorLoader,
            "OptionContext": OptionContext,
            "OptionValidator": OptionValidator,
        }
        return mapping[name]

    if name in {
        "TypeMapper",
        "UEEnum",
        "UEEnumValue",
        "UEField",
        "UEMessage",
        "UEOneofCase",
        "UEOneofWrapper",
        "UEProtoFile",
    }:
        from .type_mapper import (
            TypeMapper,
            UEEnum,
            UEEnumValue,
            UEField,
            UEMessage,
            UEOneofCase,
            UEOneofWrapper,
            UEProtoFile,
        )

        mapping = {
            "TypeMapper": TypeMapper,
            "UEEnum": UEEnum,
            "UEEnumValue": UEEnumValue,
            "UEField": UEField,
            "UEMessage": UEMessage,
            "UEOneofCase": UEOneofCase,
            "UEOneofWrapper": UEOneofWrapper,
            "UEProtoFile": UEProtoFile,
        }
        return mapping[name]

    raise AttributeError(name)
