"""Converters template generation for proto2ue Unreal Engine bindings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from .. import model
from ..type_mapper import UEField, UEMessage, UEProtoFile


@dataclass(frozen=True, slots=True)
class ConverterRenderResult:
    """Container holding the header and source bodies for generated converters."""

    header: str
    source: str


@dataclass
class ConversionError:
    """Represents an individual conversion error captured at runtime."""

    field_path: str
    message: str


class ConversionContext:
    """Collects conversion errors for python level validation used in tests."""

    def __init__(self) -> None:
        self._errors: List[ConversionError] = []

    @property
    def errors(self) -> List[ConversionError]:
        return list(self._errors)

    def add_error(self, field_path: str, message: str) -> None:
        self._errors.append(ConversionError(field_path=field_path, message=message))

    def has_errors(self) -> bool:
        return bool(self._errors)


class PythonConvertersRuntime:
    """Runtime helpers that mirror the generated C++ semantics for tests."""

    def __init__(self, ue_file: UEProtoFile) -> None:
        self._messages: Dict[str, UEMessage] = {}
        for message in ue_file.messages:
            self._register_message(message)

    # Public helpers -----------------------------------------------------
    def to_proto(
        self,
        message_full_name: str,
        ue_value: Dict[str, Any],
        proto_instance: Any,
        context: Optional[ConversionContext] = None,
    ) -> Any:
        """Populate *proto_instance* from the UE-side dictionary representation."""

        ctx = context or ConversionContext()
        message = self._messages[message_full_name]
        self._encode_message(message, ue_value, proto_instance, ctx, field_path="")
        return proto_instance

    def from_proto(
        self,
        message_full_name: str,
        proto_instance: Any,
        context: Optional[ConversionContext] = None,
    ) -> Dict[str, Any]:
        """Convert *proto_instance* into a UE-side dictionary representation."""

        ctx = context or ConversionContext()
        message = self._messages[message_full_name]
        result: Dict[str, Any] = {}
        self._decode_message(message, proto_instance, result, ctx, field_path="")
        return result

    # Registration -------------------------------------------------------
    def _register_message(self, message: UEMessage) -> None:
        if not message.source:
            raise ValueError("UEMessage is missing original protobuf metadata")
        self._messages[message.source.full_name] = message
        for nested in message.nested_messages:
            self._register_message(nested)

    # Encoding helpers ---------------------------------------------------
    def _encode_message(
        self,
        message: UEMessage,
        ue_value: Dict[str, Any],
        proto_instance: Any,
        context: ConversionContext,
        *,
        field_path: str,
    ) -> None:
        oneof_groups = self._group_oneof_fields(message.fields)

        for group_name, group_fields in oneof_groups.items():
            provided = [
                field
                for field in group_fields
                if self._is_value_provided(ue_value.get(field.name))
            ]
            if len(provided) > 1:
                context.add_error(
                    self._join_field_path(field_path, group_name),
                    "Multiple values provided for oneof",
                )

        for field in message.fields:
            value = ue_value.get(field.name)
            field_model = field.source
            if field_model is None:
                raise ValueError(f"Field '{field.name}' is missing source metadata")
            proto_field_name = field_model.name
            child_path = self._join_field_path(field_path, proto_field_name)

            if field.oneof_group:
                if not self._is_value_provided(value):
                    # oneof unset, skip entirely
                    continue
            elif field.is_optional:
                if not self._is_value_provided(value):
                    continue
            elif field.is_map:
                value = value or {}
            elif field.is_repeated:
                value = value or []
            else:
                if value is None:
                    context.add_error(child_path, "Required field missing")
                    continue

            if field.is_map:
                self._encode_map_field(field, value, proto_instance, context, child_path)
            elif field.is_repeated:
                self._encode_repeated_field(field, value, proto_instance, context, child_path)
            else:
                self._encode_singular_field(
                    field, value, proto_instance, context, child_path
                )

    def _encode_map_field(
        self,
        field: UEField,
        value: Dict[Any, Any],
        proto_instance: Any,
        context: ConversionContext,
        field_path: str,
    ) -> None:
        if not isinstance(value, dict):
            context.add_error(field_path, "Map field expects a dictionary value")
            return

        container = getattr(proto_instance, field.source.name)
        container.clear()

        map_entry = field.source.map_entry
        if map_entry is None:
            raise ValueError("Map field is missing map entry metadata")

        for key, item in value.items():
            if map_entry.value_kind is model.FieldKind.MESSAGE:
                target = container[key]
                message = map_entry.value_resolved_type
                if not isinstance(message, model.Message):
                    raise ValueError("Map value type metadata is not a message")
                ue_message = self._messages[message.full_name]
                self._encode_message(
                    ue_message,
                    item,
                    target,
                    context,
                    field_path=self._join_field_path(field_path, str(key)),
                )
            else:
                container[key] = item

    def _encode_repeated_field(
        self,
        field: UEField,
        value: Iterable[Any],
        proto_instance: Any,
        context: ConversionContext,
        field_path: str,
    ) -> None:
        if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
            context.add_error(field_path, "Repeated field expects an iterable")
            return

        container = getattr(proto_instance, field.source.name)
        container.clear()

        if field.kind is model.FieldKind.MESSAGE:
            for idx, item in enumerate(value):
                target = container.add()
                ue_message = self._child_message(field)
                self._encode_message(
                    ue_message,
                    item,
                    target,
                    context,
                    field_path=self._join_field_path(field_path, str(idx)),
                )
        else:
            container.extend(value)

    def _encode_singular_field(
        self,
        field: UEField,
        value: Any,
        proto_instance: Any,
        context: ConversionContext,
        field_path: str,
    ) -> None:
        if field.kind is model.FieldKind.MESSAGE:
            target = getattr(proto_instance, field.source.name)
            ue_message = self._child_message(field)
            self._encode_message(
                ue_message,
                value,
                target,
                context,
                field_path=field_path,
            )
        else:
            setattr(proto_instance, field.source.name, value)

    # Decoding helpers ---------------------------------------------------
    def _decode_message(
        self,
        message: UEMessage,
        proto_instance: Any,
        result: Dict[str, Any],
        context: ConversionContext,
        *,
        field_path: str,
    ) -> None:
        oneof_groups = self._group_oneof_fields(message.fields)
        for group_name, fields in oneof_groups.items():
            active = proto_instance.WhichOneof(group_name)
            for field in fields:
                child_path = self._join_field_path(field_path, field.source.name)
                if field.source.name == active:
                    value = self._decode_field_value(
                        field,
                        getattr(proto_instance, field.source.name),
                        context,
                        child_path,
                        active=True,
                    )
                    result[field.name] = value
                else:
                    result[field.name] = None

        for field in message.fields:
            if field.oneof_group:
                continue
            child_path = self._join_field_path(field_path, field.source.name)
            if field.is_map:
                result[field.name] = self._decode_map_field(
                    field, getattr(proto_instance, field.source.name), context, child_path
                )
            elif field.is_repeated:
                result[field.name] = self._decode_repeated_field(
                    field, getattr(proto_instance, field.source.name), context, child_path
                )
            elif field.kind is model.FieldKind.MESSAGE:
                if self._has_proto_field(proto_instance, field):
                    result[field.name] = self._decode_message_field(
                        field, getattr(proto_instance, field.source.name), context, child_path
                    )
                else:
                    result[field.name] = None
            elif field.is_optional:
                if self._has_proto_field(proto_instance, field):
                    result[field.name] = getattr(proto_instance, field.source.name)
                else:
                    result[field.name] = None
            else:
                result[field.name] = getattr(proto_instance, field.source.name)

    def _decode_field_value(
        self,
        field: UEField,
        value: Any,
        context: ConversionContext,
        field_path: str,
        *,
        active: bool = False,
    ) -> Any:
        if field.kind is model.FieldKind.MESSAGE:
            ue_message = self._child_message(field)
            result: Dict[str, Any] = {}
            self._decode_message(ue_message, value, result, context, field_path=field_path)
            return result
        return value

    def _decode_map_field(
        self,
        field: UEField,
        container: Any,
        context: ConversionContext,
        field_path: str,
    ) -> Dict[Any, Any]:
        result: Dict[Any, Any] = {}
        map_entry = field.source.map_entry
        if map_entry is None:
            raise ValueError("Map field missing map entry metadata")
        if map_entry.value_kind is model.FieldKind.MESSAGE:
            ue_message = self._messages[map_entry.value_resolved_type.full_name]  # type: ignore[arg-type]
            for key, value in container.items():
                child_result: Dict[str, Any] = {}
                self._decode_message(
                    ue_message,
                    value,
                    child_result,
                    context,
                    field_path=self._join_field_path(field_path, str(key)),
                )
                result[key] = child_result
        else:
            result.update(container)
        return result

    def _decode_repeated_field(
        self,
        field: UEField,
        container: Any,
        context: ConversionContext,
        field_path: str,
    ) -> List[Any]:
        if field.kind is model.FieldKind.MESSAGE:
            ue_message = self._child_message(field)
            result: List[Any] = []
            for idx, value in enumerate(container):
                child_result: Dict[str, Any] = {}
                self._decode_message(
                    ue_message,
                    value,
                    child_result,
                    context,
                    field_path=self._join_field_path(field_path, str(idx)),
                )
                result.append(child_result)
            return result
        return list(container)

    def _decode_message_field(
        self,
        field: UEField,
        value: Any,
        context: ConversionContext,
        field_path: str,
    ) -> Any:
        ue_message = self._child_message(field)
        result: Dict[str, Any] = {}
        self._decode_message(ue_message, value, result, context, field_path=field_path)
        return result

    # Utility helpers ----------------------------------------------------
    def _child_message(self, field: UEField) -> UEMessage:
        resolved = field.source.resolved_type
        if not isinstance(resolved, model.Message):
            raise ValueError("Expected field resolved type to be a message")
        return self._messages[resolved.full_name]

    def _group_oneof_fields(self, fields: Iterable[UEField]) -> Dict[str, List[UEField]]:
        groups: Dict[str, List[UEField]] = {}
        for field in fields:
            if field.oneof_group:
                groups.setdefault(field.oneof_group, []).append(field)
        return groups

    def _is_value_provided(self, value: Any) -> bool:
        if value is None:
            return False
        return True

    def _join_field_path(self, parent: str, name: str) -> str:
        if not parent:
            return name
        return f"{parent}.{name}"

    def _has_proto_field(self, proto_instance: Any, field: UEField) -> bool:
        field_name = field.source.name
        if field.oneof_group:
            return proto_instance.WhichOneof(field.oneof_group) == field_name
        try:
            return proto_instance.HasField(field_name)
        except ValueError:
            descriptor = proto_instance.DESCRIPTOR.fields_by_name[field_name]
            if descriptor.label == descriptor.LABEL_REPEATED:
                return len(getattr(proto_instance, field_name)) > 0
            value = getattr(proto_instance, field_name)
            default = descriptor.default_value
            return value != default


class ConvertersTemplate:
    """Render conversion helpers for a UE proto file."""

    def __init__(self, ue_file: UEProtoFile) -> None:
        self._ue_file = ue_file

    # Public API ---------------------------------------------------------
    def render(self) -> ConverterRenderResult:
        return ConverterRenderResult(
            header=self._render_header(),
            source=self._render_source(),
        )

    def python_runtime(self) -> PythonConvertersRuntime:
        """Return a python runtime mirroring the generated logic for testing."""

        return PythonConvertersRuntime(self._ue_file)

    # Rendering helpers --------------------------------------------------
    def _render_header(self) -> str:
        lines: List[str] = []
        lines.append("#pragma once")
        lines.append("")
        lines.append(
            f"// Generated conversion helpers by proto2ue. Source: {self._ue_file.name}"
        )
        lines.append("")
        lines.append('#include "CoreMinimal.h"')
        lines.append('#include "Kismet/BlueprintFunctionLibrary.h"')
        header_include = self._generated_header_name()
        lines.append(f'#include "{header_include}"')
        lines.append("")
        lines.append("namespace Proto2UE::Converters {")
        lines.append("")
        lines.append("struct FConversionError { FString Message; FString FieldPath; };")
        lines.append("class FConversionContext {")
        lines.append("public:")
        lines.append("    void AddError(const FString& InFieldPath, const FString& InMessage);")
        lines.append("    bool HasErrors() const;")
        lines.append("    const TArray<FConversionError>& GetErrors() const;")
        lines.append("private:")
        lines.append("    TArray<FConversionError> Errors;")
        lines.append("};")
        lines.append("")

        for message in self._collect_messages(self._ue_file.messages):
            ue_type = self._qualified_ue_type(message)
            proto_type = self._qualified_proto_type(message)
            lines.append(
                f"void ToProto(const {ue_type}& Source, {proto_type}& Out, FConversionContext* Context = nullptr);"
            )
            lines.append(
                f"bool FromProto(const {proto_type}& Source, {ue_type}& Out, FConversionContext* Context = nullptr);"
            )
            lines.append("")

        lines.append("}  // namespace Proto2UE::Converters")
        lines.append("")
        lines.append("UCLASS()")
        lines.append(
            "class UProto2UEBlueprintLibrary : public UBlueprintFunctionLibrary {"
        )
        lines.append("    GENERATED_BODY()")
        lines.append("public:")
        for message in self._ue_file.messages:
            ue_type = self._qualified_ue_type(message)
            proto_type = self._qualified_proto_type(message)
            base_name = message.ue_name[1:] if message.ue_name.startswith("F") else message.ue_name
            lines.append(
                "    UFUNCTION(BlueprintCallable, Category=\"Proto2UE\")"
            )
            lines.append(
                f"    static bool {base_name}ToProtoBytes(const {ue_type}& Source, TArray<uint8>& OutBytes, FString& Error);"
            )
            lines.append(
                "    UFUNCTION(BlueprintCallable, Category=\"Proto2UE\")"
            )
            lines.append(
                f"    static bool {base_name}FromProtoBytes(const TArray<uint8>& InBytes, {ue_type}& OutData, FString& Error);"
            )
        lines.append("};")
        lines.append("")
        return "\n".join(lines) + "\n"

    def _render_source(self) -> str:
        lines: List[str] = []
        header_include = self._generated_converters_header()
        lines.append(
            f"// Generated conversion helpers by proto2ue. Source: {self._ue_file.name}"
        )
        lines.append(f'#include "{header_include}"')
        lines.append("#include \"google/protobuf/message.h\"")
        lines.append("")
        lines.append("namespace Proto2UE::Converters {")
        lines.append("")
        lines.append("void FConversionContext::AddError(const FString& InFieldPath, const FString& InMessage) {")
        lines.append("    Errors.Emplace(FConversionError{InMessage, InFieldPath});")
        lines.append("}")
        lines.append("bool FConversionContext::HasErrors() const { return Errors.Num() > 0; }")
        lines.append(
            "const TArray<FConversionError>& FConversionContext::GetErrors() const { return Errors; }"
        )
        lines.append("")

        for message in self._collect_messages(self._ue_file.messages):
            ue_type = self._qualified_ue_type(message)
            proto_type = self._qualified_proto_type(message)
            lines.extend(
                self._render_to_proto_function(message, ue_type, proto_type)
            )
            lines.append("")
            lines.extend(
                self._render_from_proto_function(message, ue_type, proto_type)
            )
            lines.append("")

        lines.append("}  // namespace Proto2UE::Converters")
        lines.append("")
        lines.append("// Blueprint helpers are intentionally left as declarations only for game modules.")
        lines.append("")
        return "\n".join(lines) + "\n"

    def _render_to_proto_function(
        self, message: UEMessage, ue_type: str, proto_type: str
    ) -> List[str]:
        lines: List[str] = []
        lines.append(
            f"void ToProto(const {ue_type}& Source, {proto_type}& Out, FConversionContext* Context) {{"
        )
        lines.append("    Out.Clear();")
        for field in message.fields:
            source = field.source
            if source is None:
                continue
            field_name = source.name
            if field.is_map:
                lines.append(
                    f"    // Map field {field_name} handling will copy key/value pairs."
                )
                lines.append(
                    f"    for (const auto& Kvp : Source.{field.name}) {{ /* populate Out.mutable_{field_name}() */ }}"
                )
            elif field.is_repeated:
                lines.append(
                    f"    for (const auto& Item : Source.{field.name}) {{ Out.add_{field_name}(Item); }}"
                )
            elif field.kind is model.FieldKind.MESSAGE:
                lines.append(
                    f"    if (Source.{field.name}.IsSet()) {{ ToProto(Source.{field.name}.GetValue(), *Out.mutable_{field_name}(), Context); }}"
                )
            else:
                condition = (
                    f"Source.{field.name}.IsSet()" if field.is_optional else "true"
                )
                assignment = (
                    f"Out.set_{field_name}(Source.{field.name}.GetValue());"
                    if field.is_optional
                    else f"Out.set_{field_name}(Source.{field.name});"
                )
                lines.append(f"    if ({condition}) {{ {assignment} }}")
        lines.append("}")
        return lines

    def _render_from_proto_function(
        self, message: UEMessage, ue_type: str, proto_type: str
    ) -> List[str]:
        lines: List[str] = []
        lines.append(
            f"bool FromProto(const {proto_type}& Source, {ue_type}& Out, FConversionContext* Context) {{"
        )
        lines.append("    Out = {};")
        lines.append("    bool bOk = true;")
        for field in message.fields:
            source = field.source
            if source is None:
                continue
            field_name = source.name
            if field.is_map:
                lines.append(
                    f"    for (const auto& Kvp : Source.{field_name}()) {{ /* populate Out.{field.name} */ }}"
                )
            elif field.is_repeated:
                lines.append(
                    f"    for (const auto& Item : Source.{field_name}()) {{ Out.{field.name}.Add(Item); }}"
                )
            elif field.kind is model.FieldKind.MESSAGE:
                lines.append(
                    f"    if (Source.has_{field_name}()) {{ FromProto(Source.{field_name}(), Out.{field.name}.Emplace_GetRef(), Context); }}"
                )
            else:
                lines.append(f"    Out.{field.name} = Source.{field_name}();")
        lines.append("    return bOk && (!Context || !Context->HasErrors());")
        lines.append("}")
        return lines

    def _collect_messages(self, messages: Iterable[UEMessage]) -> Iterable[UEMessage]:
        for message in messages:
            yield message
            yield from self._collect_messages(message.nested_messages)

    def _qualified_proto_type(self, message: UEMessage) -> str:
        if not message.source:
            raise ValueError("UEMessage is missing source metadata")
        return "::".join(message.source.full_name.split("."))

    def _qualified_ue_type(self, message: UEMessage) -> str:
        namespace = self._ue_namespace()
        if namespace:
            return f"{namespace}::{message.ue_name}"
        return message.ue_name

    def _ue_namespace(self) -> str:
        if not self._ue_file.package:
            return ""
        return "::".join(self._ue_file.package.split("."))

    def _generated_header_name(self) -> str:
        base = self._base_name()
        return f"{base}.proto2ue.h"

    def _generated_converters_header(self) -> str:
        base = self._base_name()
        return f"{base}.proto2ue.converters.h"

    def _base_name(self) -> str:
        if self._ue_file.name.endswith(".proto"):
            return self._ue_file.name[:-6]
        return self._ue_file.name


__all__ = [
    "ConverterRenderResult",
    "ConversionContext",
    "ConversionError",
    "ConvertersTemplate",
    "PythonConvertersRuntime",
]

