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
        self._external_cache: Dict[str, UEMessage] = {}
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
        # Match the behaviour of the generated C++ runtime which clears the
        # output message before populating it to avoid leaking previous data
        # when the same proto instance is reused.
        clear = getattr(proto_instance, "Clear", None)
        if callable(clear):
            clear()
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
        full_name = message.source.full_name
        if full_name in self._messages:
            return
        self._messages[full_name] = message
        for nested in message.nested_messages:
            self._register_message(nested)
        self._register_field_dependencies(message)

    def _register_field_dependencies(self, message: UEMessage) -> None:
        for field in message.fields:
            source = field.source
            if source is None:
                raise ValueError(f"Field '{field.name}' is missing source metadata")
            if field.kind is model.FieldKind.MESSAGE:
                resolved = source.resolved_type
                if isinstance(resolved, model.Message):
                    self._ensure_model_message_registered(resolved)
            if field.is_map and source.map_entry:
                entry = source.map_entry
                if (
                    entry.value_kind is model.FieldKind.MESSAGE
                    and isinstance(entry.value_resolved_type, model.Message)
                ):
                    self._ensure_model_message_registered(entry.value_resolved_type)

    def _ensure_model_message_registered(self, message: model.Message) -> UEMessage:
        existing = self._messages.get(message.full_name)
        if existing is not None:
            return existing
        cached = self._external_cache.get(message.full_name)
        if cached is None:
            cached = self._convert_model_message(message)
            self._external_cache[message.full_name] = cached
        self._register_message(cached)
        return cached

    def _convert_model_message(self, message: model.Message) -> UEMessage:
        cached = self._external_cache.get(message.full_name)
        if cached is not None:
            return cached

        ue_message = UEMessage(
            name=message.name,
            full_name=message.full_name,
            ue_name=message.name,
            fields=[],
            nested_messages=[],
            nested_enums=[],
            oneofs=[],
            blueprint_type=True,
            struct_specifiers=[],
            struct_metadata={},
            category=None,
            source=message,
        )
        self._external_cache[message.full_name] = ue_message

        ue_message.fields = [self._convert_model_field(field) for field in message.fields]
        ue_message.nested_messages = [
            self._convert_model_message(nested) for nested in message.nested_messages
        ]
        return ue_message

    def _convert_model_field(self, field: model.Field) -> UEField:
        is_map = field.kind is model.FieldKind.MAP
        is_repeated = field.cardinality is model.FieldCardinality.REPEATED and not is_map
        is_optional = (
            field.cardinality is model.FieldCardinality.OPTIONAL and field.oneof is None
        )

        base_type = field.type_name or field.scalar or ""
        ue_type = base_type

        map_key_type: Optional[str]
        map_value_type: Optional[str]
        map_key_type = None
        map_value_type = None
        if field.map_entry:
            map_key_type = field.map_entry.key_type_name or field.map_entry.key_scalar or ""
            map_value_type = (
                field.map_entry.value_type_name or field.map_entry.value_scalar or ""
            )

        return UEField(
            name=field.name,
            number=field.number,
            base_type=base_type,
            ue_type=ue_type,
            kind=field.kind,
            cardinality=field.cardinality,
            is_optional=is_optional,
            is_repeated=is_repeated,
            is_map=is_map,
            container=None,
            map_key_type=map_key_type,
            map_value_type=map_value_type,
            oneof_group=field.oneof,
            json_name=field.json_name,
            default_value=field.default_value,
            blueprint_exposed=True,
            blueprint_read_only=False,
            uproperty_specifiers=[],
            uproperty_metadata={},
            category=None,
            source=field,
        )

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
        lines.append('#include <string>')
        lines.append('#include <type_traits>')
        lines.append('#include <utility>')
        lines.append('#include "Kismet/BlueprintFunctionLibrary.h"')
        header_include = self._generated_header_name()
        lines.append(f'#include "{header_include}"')
        proto_header_include = self._proto_message_header_name()
        lines.append(f'#include "{proto_header_include}"')
        for include in self._dependency_converter_includes():
            lines.append(f'#include "{include}"')
        lines.append("")
        lines.append("namespace Proto2UE::Converters {")
        lines.append("")
        lines.extend(self._render_internal_namespace())
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
        for include in self._dependency_converter_includes():
            lines.append(f'#include "{include}"')
        lines.append("#include \"google/protobuf/message.h\"")
        lines.append("#include <string>")
        lines.append("#include <type_traits>")
        lines.append("#include <utility>")
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
        lines.append("namespace {")
        lines.append(
            "FString FormatConversionErrors(const Proto2UE::Converters::FConversionContext& Context) {"
        )
        lines.append("    FString Combined;")
        lines.append("    const auto& Errors = Context.GetErrors();")
        lines.append("    for (const auto& ConversionError : Errors) {")
        lines.append("        if (!Combined.IsEmpty()) {")
        lines.append("            Combined += TEXT(\"; \");")
        lines.append("        }")
        lines.append("        if (!ConversionError.FieldPath.IsEmpty()) {")
        lines.append("            Combined += ConversionError.FieldPath;")
        lines.append("            Combined += TEXT(\": \");")
        lines.append("        }")
        lines.append("        Combined += ConversionError.Message;")
        lines.append("    }")
        lines.append("    if (Combined.IsEmpty()) {")
        lines.append("        return FString(TEXT(\"Unknown conversion error.\"));")
        lines.append("    }")
        lines.append("    return Combined;")
        lines.append("}")
        lines.append("}  // namespace")
        lines.append("")
        for message in self._ue_file.messages:
            ue_type = self._qualified_ue_type(message)
            proto_type = self._qualified_proto_type(message)
            base_name = message.ue_name[1:] if message.ue_name.startswith("F") else message.ue_name
            lines.append(
                f"bool UProto2UEBlueprintLibrary::{base_name}ToProtoBytes(const {ue_type}& Source, TArray<uint8>& OutBytes, FString& Error) {{"
            )
            lines.append("    Proto2UE::Converters::FConversionContext Context;")
            lines.append(f"    {proto_type} ProtoMessage;")
            lines.append(
                "    Proto2UE::Converters::ToProto(Source, ProtoMessage, &Context);"
            )
            lines.append("    if (Context.HasErrors()) {")
            lines.append("        Error = FormatConversionErrors(Context);")
            lines.append("        return false;")
            lines.append("    }")
            lines.append("    std::string Serialized;")
            lines.append("    if (!ProtoMessage.SerializeToString(&Serialized)) {")
            lines.append(
                "        Error = TEXT(\"Failed to serialize protobuf message.\");"
            )
            lines.append("        return false;")
            lines.append("    }")
            lines.append(
                "    OutBytes = Proto2UE::Converters::Internal::FromProtoBytes(Serialized);"
            )
            lines.append("    Error = FString();")
            lines.append("    return true;")
            lines.append("}")
            lines.append("")
            lines.append(
                f"bool UProto2UEBlueprintLibrary::{base_name}FromProtoBytes(const TArray<uint8>& InBytes, {ue_type}& OutData, FString& Error) {{"
            )
            lines.append("    const std::string Serialized = Proto2UE::Converters::Internal::ToProtoBytes(InBytes);")
            lines.append(f"    {proto_type} ProtoMessage;")
            lines.append("    if (!ProtoMessage.ParseFromString(Serialized)) {")
            lines.append(
                "        Error = TEXT(\"Failed to parse protobuf bytes.\");"
            )
            lines.append("        return false;")
            lines.append("    }")
            lines.append("    Proto2UE::Converters::FConversionContext Context;")
            lines.append(
                "    if (!Proto2UE::Converters::FromProto(ProtoMessage, OutData, &Context)) {"
            )
            lines.append("        Error = FormatConversionErrors(Context);")
            lines.append("        return false;")
            lines.append("    }")
            lines.append("    Error = FString();")
            lines.append("    return true;")
            lines.append("}")
            lines.append("")
        return "\n".join(lines) + "\n"

    def _render_internal_namespace(self) -> List[str]:
        lines: List[str] = []
        lines.append("namespace Internal {")
        lines.append("template <typename, typename = void>")
        lines.append("struct THasIsSet : std::false_type {};")
        lines.append("template <typename T>")
        lines.append(
            "struct THasIsSet<T, std::void_t<decltype(std::declval<const T&>().IsSet())>> : std::true_type {};"
        )
        lines.append("template <typename, typename = void>")
        lines.append("struct THasIsSetMember : std::false_type {};")
        lines.append("template <typename T>")
        lines.append(
            "struct THasIsSetMember<T, std::void_t<decltype(std::declval<const T&>().bIsSet)>> : std::true_type {};"
        )
        lines.append("template <typename, typename = void>")
        lines.append("struct THasNum : std::false_type {};")
        lines.append("template <typename T>")
        lines.append(
            "struct THasNum<T, std::void_t<decltype(std::declval<const T&>().Num())>> : std::true_type {};"
        )
        lines.append("template <typename, typename = void>")
        lines.append("struct THasEquality : std::false_type {};")
        lines.append("template <typename T>")
        lines.append(
            "struct THasEquality<T, std::void_t<decltype(std::declval<const T&>() == std::declval<const T&>())>> : std::true_type {};"
        )
        lines.append("template <typename, typename = void>")
        lines.append("struct THasGetValue : std::false_type {};")
        lines.append("template <typename T>")
        lines.append(
            "struct THasGetValue<T, std::void_t<decltype(std::declval<const T&>().GetValue())>> : std::true_type {};"
        )
        lines.append("template <typename, typename = void>")
        lines.append("struct THasValueMember : std::false_type {};")
        lines.append("template <typename T>")
        lines.append(
            "struct THasValueMember<T, std::void_t<decltype(std::declval<const T&>().Value)>> : std::true_type {};"
        )
        lines.append("template <typename T>")
        lines.append("bool IsValueProvided(const T& Value) {")
        lines.append("    if constexpr (THasIsSet<T>::value) {")
        lines.append("        return Value.IsSet();")
        lines.append("    } else if constexpr (THasIsSetMember<T>::value) {")
        lines.append("        return Value.bIsSet;")
        lines.append("    } else if constexpr (THasNum<T>::value) {")
        lines.append("        return Value.Num() > 0;")
        lines.append("    } else if constexpr (std::is_pointer_v<T>) {")
        lines.append("        return Value != nullptr;")
        lines.append("    } else if constexpr (THasEquality<T>::value && std::is_default_constructible_v<T>) {")
        lines.append("        return Value != T{};")
        lines.append("    } else {")
        lines.append("        return false;")
        lines.append("    }")
        lines.append("}")
        lines.append("template <typename T>")
        lines.append("decltype(auto) GetFieldValue(const T& Value) {")
        lines.append("    if constexpr (THasGetValue<T>::value) {")
        lines.append("        return Value.GetValue();")
        lines.append("    } else if constexpr (THasValueMember<T>::value) {")
        lines.append("        return Value.Value;")
        lines.append("    } else {")
        lines.append("        return Value;")
        lines.append("    }")
        lines.append("}")
        lines.append("inline std::string ToProtoString(const FString& Value) {")
        lines.append("    FTCHARToUTF8 Converter(*Value);")
        lines.append("    return std::string(Converter.Get(), Converter.Length());")
        lines.append("}")
        lines.append("inline std::string ToProtoBytes(const TArray<uint8>& Value) {")
        lines.append(
            "    return std::string(reinterpret_cast<const char*>(Value.GetData()), Value.Num());"
        )
        lines.append("}")
        lines.append("inline FString FromProtoString(const std::string& Value) {")
        lines.append("    return FString(UTF8_TO_TCHAR(Value.c_str()));")
        lines.append("}")
        lines.append("inline TArray<uint8> FromProtoBytes(const std::string& Value) {")
        lines.append("    TArray<uint8> Result;")
        lines.append(
            "    Result.Append(reinterpret_cast<const uint8*>(Value.data()), Value.size());"
        )
        lines.append("    return Result;")
        lines.append("}")
        lines.append("}  // namespace Internal")
        return lines

    def _render_to_proto_function(
        self, message: UEMessage, ue_type: str, proto_type: str
    ) -> List[str]:
        lines: List[str] = []
        lines.append(
            f"void ToProto(const {ue_type}& Source, {proto_type}& Out, FConversionContext* Context) {{"
        )
        lines.append("    Out.Clear();")
        oneof_groups = self._group_oneof_fields(message.fields)
        for group_name, group_fields in oneof_groups.items():
            lines.extend(self._render_to_proto_oneof_group(group_name, group_fields))
        for field in message.fields:
            source = field.source
            if source is None:
                continue
            if field.oneof_group:
                continue
            field_name = source.name
            if field.is_map:
                map_entry = field.source.map_entry
                if map_entry is None:
                    raise ValueError("Map field is missing map entry metadata")
                map_container = f"ProtoMap_{field.name}"
                lines.append(
                    f"    auto& {map_container} = *Out.mutable_{field_name}();"
                )
                if map_entry.value_kind is model.FieldKind.MESSAGE:
                    lines.append(
                        f"    for (const auto& Kvp : Source.{field.name}) {{"
                    )
                    key_expr = "Kvp.Key"
                    proto_key_expr = self._to_proto_map_key(field, key_expr)
                    if proto_key_expr != key_expr:
                        key_var = f"ProtoKey_{field.name}"
                        lines.append(
                            f"        const auto {key_var} = {proto_key_expr};"
                        )
                        key_expr = key_var
                    lines.append(
                        f"        auto& Added = {map_container}[{key_expr}];"
                    )
                    lines.append(
                        "        ToProto(Kvp.Value, Added, Context);"
                    )
                    lines.append("    }")
                else:
                    lines.append(
                        f"    for (const auto& Kvp : Source.{field.name}) {{"
                    )
                    key_expr = "Kvp.Key"
                    proto_key_expr = self._to_proto_map_key(field, key_expr)
                    if proto_key_expr != key_expr:
                        key_var = f"ProtoKey_{field.name}"
                        lines.append(
                            f"        const auto {key_var} = {proto_key_expr};"
                        )
                        key_expr = key_var
                    value_expr = "Kvp.Value"
                    if map_entry.value_kind is model.FieldKind.ENUM:
                        proto_type = self._qualified_proto_map_value_enum_type(field)
                        value_expr = f"static_cast<{proto_type}>({value_expr})"
                    else:
                        value_expr = self._to_proto_map_value(field, value_expr)
                    lines.append(
                        f"        {map_container}[{key_expr}] = {value_expr};"
                    )
                    lines.append("    }")
            elif field.is_repeated:
                if field.kind is model.FieldKind.MESSAGE:
                    lines.append(
                        f"    for (const auto& Item : Source.{field.name}) {{"
                    )
                    lines.append(
                        f"        auto* Added = Out.add_{field_name}();"
                    )
                    lines.append(
                        "        ToProto(Item, *Added, Context);"
                    )
                    lines.append("    }")
                else:
                    item_expr = "Item"
                    if field.kind is model.FieldKind.ENUM:
                        proto_type = self._qualified_proto_enum_type(field)
                        item_expr = f"static_cast<{proto_type}>(Item)"
                    else:
                        item_expr = self._to_proto_value(field, item_expr)
                    lines.append(
                        f"    for (const auto& Item : Source.{field.name}) {{ Out.add_{field_name}({item_expr}); }}"
                    )
            elif field.kind is model.FieldKind.MESSAGE:
                if field.is_optional:
                    lines.append(
                        f"    if (Internal::IsValueProvided(Source.{field.name})) {{"
                    )
                    lines.append(
                        f"        ToProto(Internal::GetFieldValue(Source.{field.name}), *Out.mutable_{field_name}(), Context);"
                    )
                    lines.append("    }")
                else:
                    lines.append(
                        f"    ToProto(Source.{field.name}, *Out.mutable_{field_name}(), Context);"
                    )
            else:
                if field.is_optional:
                    condition = (
                        f"Internal::IsValueProvided(Source.{field.name})"
                    )
                    value_expr = (
                        f"Internal::GetFieldValue(Source.{field.name})"
                    )
                else:
                    condition = "true"
                    value_expr = f"Source.{field.name}"
                if field.kind is model.FieldKind.ENUM:
                    proto_type = self._qualified_proto_enum_type(field)
                    value_expr = f"static_cast<{proto_type}>({value_expr})"
                else:
                    value_expr = self._to_proto_value(field, value_expr)
                assignment = f"Out.set_{field_name}({value_expr});"
                lines.append(f"    if ({condition}) {{ {assignment} }}")
        lines.append("}")
        return lines

    def _render_to_proto_oneof_group(
        self, group_name: str, fields: List[UEField]
    ) -> List[str]:
        if not fields:
            return []
        lines: List[str] = []
        guard_var = f"bHas{self._to_pascal_case(group_name)}Value"
        lines.append("    {")
        lines.append(f"        bool {guard_var} = false;")
        lines.append(f"        const TCHAR* FieldPath = TEXT(\"{group_name}\");")
        for field in fields:
            source = field.source
            if source is None:
                continue
            field_name = source.name
            lines.append(
                f"        if (Internal::IsValueProvided(Source.{field.name})) {{"
            )
            lines.append(f"            if ({guard_var}) {{")
            lines.append("                if (Context) {")
            lines.append(
                "                    Context->AddError(FieldPath, TEXT(\"Multiple values provided for oneof\"));"
            )
            lines.append("                }")
            lines.append("                continue;")
            lines.append("            }")
            lines.append(f"            {guard_var} = true;")
            lines.extend(
                self._render_to_proto_oneof_assignment(field, field_name, indent="            ")
            )
            lines.append("        }")
        lines.append("    }")
        return lines

    def _render_to_proto_oneof_assignment(
        self, field: UEField, field_name: str, *, indent: str
    ) -> List[str]:
        value_expr = f"Internal::GetFieldValue(Source.{field.name})"
        lines = [f"{indent}const auto& ActiveValue = {value_expr};"]
        if field.kind is model.FieldKind.MESSAGE:
            lines.append(
                f"{indent}ToProto(ActiveValue, *Out.mutable_{field_name}(), Context);"
            )
        else:
            value_expr = "ActiveValue"
            if field.kind is model.FieldKind.ENUM:
                proto_type = self._qualified_proto_enum_type(field)
                value_expr = f"static_cast<{proto_type}>({value_expr})"
            else:
                value_expr = self._to_proto_value(field, value_expr)
            lines.append(f"{indent}Out.set_{field_name}({value_expr});")
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
        oneof_groups = self._group_oneof_fields(message.fields)
        for group_name, group_fields in oneof_groups.items():
            lines.extend(
                self._render_from_proto_oneof_group(proto_type, group_name, group_fields)
            )
        for field in message.fields:
            source = field.source
            if source is None:
                continue
            if field.oneof_group:
                continue
            field_name = source.name
            if field.is_map:
                map_entry = field.source.map_entry
                if map_entry is None:
                    raise ValueError("Map field is missing map entry metadata")
                lines.append(
                    f"    for (const auto& Kvp : Source.{field_name}()) {{"
                )
                key_expr = "Kvp.first"
                proto_key_expr = self._from_proto_map_key(field, key_expr)
                if proto_key_expr != key_expr:
                    key_var = f"Key_{field.name}"
                    lines.append(
                        f"        const auto {key_var} = {proto_key_expr};"
                    )
                    key_expr = key_var
                if map_entry.value_kind is model.FieldKind.MESSAGE:
                    value_type = field.map_value_type or "auto"
                    lines.append(
                        f"        {value_type} Value;"
                    )
                    lines.append(
                        "        bOk = FromProto(Kvp.second, Value, Context) && bOk;"
                    )
                    lines.append(
                        f"        Out.{field.name}.Add({key_expr}, Value);"
                    )
                else:
                    value_expr = "Kvp.second"
                    if map_entry.value_kind is model.FieldKind.ENUM:
                        value_type = field.map_value_type or "auto"
                        value_expr = f"static_cast<{value_type}>({value_expr})"
                    else:
                        value_expr = self._from_proto_map_value(field, value_expr)
                    lines.append(
                        f"        Out.{field.name}.Add({key_expr}, {value_expr});"
                    )
                lines.append("    }")
            elif field.is_repeated:
                if field.kind is model.FieldKind.MESSAGE:
                    lines.append(
                        f"    for (const auto& Item : Source.{field_name}()) {{"
                    )
                    lines.append(
                        f"        auto& Added = Out.{field.name}.Emplace_GetRef();"
                    )
                    lines.append(
                        "        bOk = FromProto(Item, Added, Context) && bOk;"
                    )
                    lines.append("    }")
                else:
                    item_expr = "Item"
                    if field.kind is model.FieldKind.ENUM:
                        item_expr = f"static_cast<{field.base_type}>(Item)"
                    else:
                        item_expr = self._from_proto_value(field, item_expr)
                    lines.append(
                        f"    for (const auto& Item : Source.{field_name}()) {{ Out.{field.name}.Add({item_expr}); }}"
                    )
            elif field.kind is model.FieldKind.MESSAGE:
                if field.is_optional:
                    lines.append(
                        f"    if (Source.has_{field_name}()) {{"
                    )
                    wrapper = field.optional_wrapper
                    if wrapper is None:
                        lines.append(
                            f"        auto& Dest = Out.{field.name}.Emplace();"
                        )
                        lines.append(
                            "        bOk = FromProto(Source.{field_name}(), Dest, Context) && bOk;"
                        )
                    else:
                        value_member = wrapper.value_member
                        is_set_member = wrapper.is_set_member
                        lines.append(
                            f"        auto& Dest = Out.{field.name}.{value_member};"
                        )
                        lines.append("        Dest = {};")
                        lines.append(
                            f"        Out.{field.name}.{is_set_member} = true;"
                        )
                        lines.append(
                            "        bOk = FromProto(Source.{field_name}(), Dest, Context) && bOk;"
                        )
                    lines.append("    }")
                else:
                    lines.append(
                        f"    bOk = FromProto(Source.{field_name}(), Out.{field.name}, Context) && bOk;"
                    )
            else:
                if field.is_optional:
                    value_expr = f"Source.{field_name}()"
                    if field.kind is model.FieldKind.ENUM:
                        value_expr = f"static_cast<{field.base_type}>({value_expr})"
                    else:
                        value_expr = self._from_proto_value(field, value_expr)
                    wrapper = field.optional_wrapper
                    if wrapper is None:
                        lines.append(
                            f"    if (Source.has_{field_name}()) {{ Out.{field.name} = {value_expr}; }}"
                        )
                    else:
                        lines.append(
                            f"    if (Source.has_{field_name}()) {{"
                        )
                        lines.append(
                            f"        Out.{field.name}.{wrapper.value_member} = {value_expr};"
                        )
                        lines.append(
                            f"        Out.{field.name}.{wrapper.is_set_member} = true;"
                        )
                        lines.append("    }")
                else:
                    value_expr = f"Source.{field_name}()"
                    if field.kind is model.FieldKind.ENUM:
                        value_expr = f"static_cast<{field.base_type}>({value_expr})"
                    else:
                        value_expr = self._from_proto_value(field, value_expr)
                    lines.append(f"    Out.{field.name} = {value_expr};")
        lines.append("    return bOk && (!Context || !Context->HasErrors());")
        lines.append("}")
        return lines

    def _render_from_proto_oneof_group(
        self, proto_type: str, group_name: str, fields: List[UEField]
    ) -> List[str]:
        if not fields:
            return []
        lines: List[str] = []
        lines.append("    {")
        case_enum = f"{proto_type}::{self._to_pascal_case(group_name)}Case"
        lines.append(f"        const auto ActiveCase = Source.{group_name}_case();")
        lines.append("        switch (ActiveCase) {")
        for field in fields:
            source = field.source
            if source is None:
                continue
            field_name = source.name
            case_name = f"{case_enum}::k{self._to_pascal_case(field_name)}"
            lines.append(f"        case {case_name}: {{")
            if field.kind is model.FieldKind.MESSAGE:
                if field.is_optional:
                    wrapper = field.optional_wrapper
                    if wrapper is None:
                        lines.append(
                            f"            auto& Dest = Out.{field.name}.Emplace();"
                        )
                        lines.append(
                            f"            bOk = FromProto(Source.{field_name}(), Dest, Context) && bOk;"
                        )
                    else:
                        value_member = wrapper.value_member
                        is_set_member = wrapper.is_set_member
                        lines.append(
                            f"            auto& Dest = Out.{field.name}.{value_member};"
                        )
                        lines.append("            Dest = {};")
                        lines.append(
                            f"            Out.{field.name}.{is_set_member} = true;"
                        )
                        lines.append(
                            f"            bOk = FromProto(Source.{field_name}(), Dest, Context) && bOk;"
                        )
                else:
                    lines.append(
                        f"            bOk = FromProto(Source.{field_name}(), Out.{field.name}, Context) && bOk;"
                    )
            else:
                value_expr = f"Source.{field_name}()"
                if field.kind is model.FieldKind.ENUM:
                    value_expr = f"static_cast<{field.base_type}>({value_expr})"
                else:
                    value_expr = self._from_proto_value(field, value_expr)
                if field.is_optional:
                    wrapper = field.optional_wrapper
                    if wrapper is None:
                        lines.append(
                            f"            Out.{field.name} = {value_expr};"
                        )
                    else:
                        lines.append(
                            f"            Out.{field.name}.{wrapper.value_member} = {value_expr};"
                        )
                        lines.append(
                            f"            Out.{field.name}.{wrapper.is_set_member} = true;"
                        )
                else:
                    lines.append(
                        f"            Out.{field.name} = {value_expr};"
                    )
            lines.append("            break;")
            lines.append("        }")
        lines.append("        default:")
        lines.append("            break;")
        lines.append("        }")
        lines.append("    }")
        return lines

    def _field_scalar_type(self, field: UEField) -> Optional[str]:
        source = field.source
        if source is None:
            return None
        if field.kind is model.FieldKind.SCALAR:
            return source.scalar
        return None

    def _map_key_scalar_type(self, field: UEField) -> Optional[str]:
        source = field.source
        if source is None or source.map_entry is None:
            return None
        entry = source.map_entry
        if entry.key_kind is model.FieldKind.SCALAR:
            return entry.key_scalar
        return None

    def _map_value_scalar_type(self, field: UEField) -> Optional[str]:
        source = field.source
        if source is None or source.map_entry is None:
            return None
        entry = source.map_entry
        if entry.value_kind is model.FieldKind.SCALAR:
            return entry.value_scalar
        return None

    def _to_proto_value(self, field: UEField, value_expr: str) -> str:
        scalar = self._field_scalar_type(field)
        if scalar == "string":
            return f"Internal::ToProtoString({value_expr})"
        if scalar == "bytes":
            return f"Internal::ToProtoBytes({value_expr})"
        return value_expr

    def _from_proto_value(self, field: UEField, value_expr: str) -> str:
        scalar = self._field_scalar_type(field)
        if scalar == "string":
            return f"Internal::FromProtoString({value_expr})"
        if scalar == "bytes":
            return f"Internal::FromProtoBytes({value_expr})"
        return value_expr

    def _to_proto_map_key(self, field: UEField, key_expr: str) -> str:
        scalar = self._map_key_scalar_type(field)
        if scalar == "string":
            return f"Internal::ToProtoString({key_expr})"
        return key_expr

    def _from_proto_map_key(self, field: UEField, key_expr: str) -> str:
        scalar = self._map_key_scalar_type(field)
        if scalar == "string":
            return f"Internal::FromProtoString({key_expr})"
        return key_expr

    def _to_proto_map_value(self, field: UEField, value_expr: str) -> str:
        scalar = self._map_value_scalar_type(field)
        if scalar == "string":
            return f"Internal::ToProtoString({value_expr})"
        if scalar == "bytes":
            return f"Internal::ToProtoBytes({value_expr})"
        return value_expr

    def _from_proto_map_value(self, field: UEField, value_expr: str) -> str:
        scalar = self._map_value_scalar_type(field)
        if scalar == "string":
            return f"Internal::FromProtoString({value_expr})"
        if scalar == "bytes":
            return f"Internal::FromProtoBytes({value_expr})"
        return value_expr

    def _to_pascal_case(self, value: str) -> str:
        parts = [part for part in value.split("_") if part]
        return "".join(part[:1].upper() + part[1:] for part in parts) or value.title()

    def _collect_messages(self, messages: Iterable[UEMessage]) -> Iterable[UEMessage]:
        for message in messages:
            yield message
            yield from self._collect_messages(message.nested_messages)

    def _qualified_proto_type(self, message: UEMessage) -> str:
        if not message.source:
            raise ValueError("UEMessage is missing source metadata")
        return "::".join(message.source.full_name.split("."))

    def _qualified_proto_enum_type(self, field: UEField) -> str:
        source = field.source
        if source is None:
            raise ValueError("Field is missing source metadata")
        resolved = source.resolved_type
        if isinstance(resolved, model.Enum):
            return self._format_proto_type_name(resolved.full_name)
        if source.type_name:
            return self._format_proto_type_name(source.type_name)
        raise ValueError("Enum field is missing type information")

    def _qualified_proto_map_value_enum_type(self, field: UEField) -> str:
        source = field.source
        if source is None or source.map_entry is None:
            raise ValueError("Map field is missing source metadata")
        entry = source.map_entry
        resolved = entry.value_resolved_type
        if isinstance(resolved, model.Enum):
            return self._format_proto_type_name(resolved.full_name)
        if entry.value_type_name:
            return self._format_proto_type_name(entry.value_type_name)
        raise ValueError("Map enum value is missing type information")

    def _format_proto_type_name(self, name: str) -> str:
        stripped = name.lstrip(".")
        if not stripped:
            raise ValueError("Cannot qualify an empty proto type name")
        return "::".join(stripped.split("."))

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

    def _proto_message_header_name(self) -> str:
        base = self._base_name()
        return f"{base}.pb.h"

    def _dependency_converter_includes(self) -> List[str]:
        source = self._ue_file.source
        if source is None:
            return []
        includes = []
        seen = set()
        for dependency in source.dependencies:
            if dependency == source.name:
                continue
            base = dependency[:-6] if dependency.endswith(".proto") else dependency
            include = f"{base}.proto2ue.converters.h"
            if include not in seen:
                seen.add(include)
                includes.append(include)
        return sorted(includes)

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

