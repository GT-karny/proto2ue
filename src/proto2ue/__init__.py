"""proto2ue package initialization."""

from __future__ import annotations

from . import model

__all__ = [
    "DescriptorLoader",
    "OptionContext",
    "OptionValidator",
    "DefaultTemplateRenderer",
    "GeneratedFile",
    "ITemplateRenderer",
    "GeneratorConfig",
    "model",
    "TypeMapper",
    "UEEnum",
    "UEEnumValue",
    "UEField",
    "UEMessage",
    "UEOneofCase",
    "UEOneofWrapper",
    "UEOptionalWrapper",
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

    if name in {"DefaultTemplateRenderer", "GeneratedFile", "ITemplateRenderer"}:
        from .codegen import DefaultTemplateRenderer, GeneratedFile, ITemplateRenderer

        mapping = {
            "DefaultTemplateRenderer": DefaultTemplateRenderer,
            "GeneratedFile": GeneratedFile,
            "ITemplateRenderer": ITemplateRenderer,
        }
        return mapping[name]

    if name == "GeneratorConfig":
        from .config import GeneratorConfig

        return GeneratorConfig

    if name in {
        "TypeMapper",
        "UEEnum",
        "UEEnumValue",
        "UEField",
        "UEMessage",
        "UEOneofCase",
        "UEOneofWrapper",
        "UEOptionalWrapper",
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
            UEOptionalWrapper,
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
            "UEOptionalWrapper": UEOptionalWrapper,
            "UEProtoFile": UEProtoFile,
        }
        return mapping[name]

    raise AttributeError(name)
