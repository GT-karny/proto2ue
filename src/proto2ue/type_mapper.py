"""Mapping utilities to transform protobuf model types into UE-friendly dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Dict, List, Optional, Tuple

from . import model


@dataclass(slots=True)
class UEEnumValue:
    """Represents a UE enum value converted from a protobuf enum value."""

    name: str
    number: int
    source: model.EnumValue


@dataclass(slots=True)
class UEEnum:
    """Represents a UE enum."""

    name: str
    full_name: str
    ue_name: str
    values: List[UEEnumValue] = field(default_factory=list)
    source: model.Enum | None = None


@dataclass(slots=True)
class UEField:
    """Represents a UE field mapped from a protobuf field."""

    name: str
    number: int
    base_type: str
    ue_type: str
    kind: model.FieldKind
    cardinality: model.FieldCardinality
    is_optional: bool
    is_repeated: bool
    is_map: bool
    container: Optional[str]
    map_key_type: Optional[str]
    map_value_type: Optional[str]
    oneof_group: Optional[str]
    json_name: Optional[str]
    default_value: Optional[str]
    source: model.Field | None = None


@dataclass(slots=True)
class UEOneofCase:
    """Represents a case within a UE oneof wrapper."""

    name: str
    ue_case_name: str
    field: UEField


@dataclass(slots=True)
class UEOneofWrapper:
    """Represents a UE wrapper generated for a protobuf oneof declaration."""

    name: str
    full_name: str
    ue_name: str
    cases: List[UEOneofCase] = field(default_factory=list)
    source: model.Oneof | None = None


@dataclass(slots=True)
class UEMessage:
    """Represents a UE message."""

    name: str
    full_name: str
    ue_name: str
    fields: List[UEField] = field(default_factory=list)
    nested_messages: List["UEMessage"] = field(default_factory=list)
    nested_enums: List[UEEnum] = field(default_factory=list)
    oneofs: List[UEOneofWrapper] = field(default_factory=list)
    source: model.Message | None = None


@dataclass(slots=True)
class UEProtoFile:
    """Represents a UE view of a protobuf file."""

    name: str
    package: Optional[str]
    messages: List[UEMessage] = field(default_factory=list)
    enums: List[UEEnum] = field(default_factory=list)
    source: model.ProtoFile | None = None


@dataclass(slots=True)
class _UESymbol:
    kind: str
    ue_name: str


class TypeMapper:
    """Maps `proto2ue.model` dataclasses into Unreal Engine focused dataclasses."""

    _SCALAR_MAPPING: Dict[str, str] = {
        "double": "double",
        "float": "float",
        "int64": "int64",
        "uint64": "uint64",
        "int32": "int32",
        "fixed64": "uint64",
        "fixed32": "uint32",
        "bool": "bool",
        "string": "FString",
        "bytes": "TArray<uint8>",
        "uint32": "uint32",
        "sfixed32": "int32",
        "sfixed64": "int64",
        "sint32": "int32",
        "sint64": "int64",
    }

    def __init__(
        self,
        *,
        message_prefix: str = "F",
        enum_prefix: str = "E",
        optional_wrapper: str = "TOptional",
        array_wrapper: str = "TArray",
        map_wrapper: str = "TMap",
    ) -> None:
        self._message_prefix = message_prefix
        self._enum_prefix = enum_prefix
        self._optional_wrapper = optional_wrapper
        self._array_wrapper = array_wrapper
        self._map_wrapper = map_wrapper
        self._symbol_table: Dict[str, _UESymbol] = {}
        self._package: Optional[str] = None

    def map_file(self, proto_file: model.ProtoFile) -> UEProtoFile:
        """Convert a :class:`model.ProtoFile` into :class:`UEProtoFile`."""

        self._package = proto_file.package
        self._symbol_table = {}
        for enum in proto_file.enums:
            self._register_enum(enum)
        for message in proto_file.messages:
            self._register_message(message)

        messages = [self._convert_message(message) for message in proto_file.messages]
        enums = [self._convert_enum(enum) for enum in proto_file.enums]
        return UEProtoFile(
            name=proto_file.name,
            package=proto_file.package,
            messages=messages,
            enums=enums,
            source=proto_file,
        )

    # Symbol table helpers -------------------------------------------------
    def _register_enum(self, enum: model.Enum) -> None:
        ue_name = self._compose_type_name(self._enum_prefix, enum.full_name)
        self._symbol_table[enum.full_name] = _UESymbol("enum", ue_name)

    def _register_message(self, message: model.Message) -> None:
        ue_name = self._compose_type_name(self._message_prefix, message.full_name)
        self._symbol_table[message.full_name] = _UESymbol("message", ue_name)

        for nested_enum in message.nested_enums:
            self._register_enum(nested_enum)
        for nested_message in message.nested_messages:
            self._register_message(nested_message)

    def _compose_type_name(self, prefix: str, full_name: str) -> str:
        relative_path = self._relative_symbol_path(full_name)
        pascal_segments = [self._to_pascal_case(segment) for segment in relative_path]
        return prefix + "".join(pascal_segments)

    def _relative_symbol_path(self, full_name: str) -> List[str]:
        if not full_name:
            return []
        package = self._package
        if package and full_name.startswith(f"{package}."):
            remainder = full_name[len(package) + 1 :]
        else:
            remainder = full_name
        return [segment for segment in remainder.split(".") if segment]

    _PASCAL_CASE_PATTERN = re.compile(r"[_\s]+")

    def _to_pascal_case(self, name: str) -> str:
        if not name:
            return name
        parts = [part for part in self._PASCAL_CASE_PATTERN.split(name) if part]
        if not parts:
            return name
        return "".join(part[:1].upper() + part[1:] for part in parts)

    def _lookup_symbol(self, proto_type: model.ProtoType | None, type_name: Optional[str]) -> str:
        full_name: Optional[str] = None
        if proto_type is not None:
            full_name = proto_type.full_name
        elif type_name is not None:
            full_name = type_name
        if not full_name:
            raise ValueError("Unable to resolve type without a full name")
        symbol = self._symbol_table.get(full_name)
        if symbol is None:
            raise KeyError(f"Type '{full_name}' was not registered in the UE symbol table")
        return symbol.ue_name

    # Conversion helpers ---------------------------------------------------
    def _convert_enum(self, enum: model.Enum) -> UEEnum:
        ue_name = self._lookup_symbol(enum, enum.full_name)
        values = [
            UEEnumValue(name=value.name, number=value.number, source=value)
            for value in enum.values
        ]
        return UEEnum(
            name=enum.name,
            full_name=enum.full_name,
            ue_name=ue_name,
            values=values,
            source=enum,
        )

    def _convert_message(self, message: model.Message) -> UEMessage:
        ue_name = self._lookup_symbol(message, message.full_name)

        fields: List[UEField] = []
        field_map: Dict[int, UEField] = {}
        for field in message.fields:
            ue_field = self._convert_field(field)
            fields.append(ue_field)
            field_map[id(field)] = ue_field

        nested_messages = [self._convert_message(nested) for nested in message.nested_messages]
        nested_enums = [self._convert_enum(enum) for enum in message.nested_enums]
        oneofs = [self._convert_oneof(oneof, field_map, ue_name) for oneof in message.oneofs]

        return UEMessage(
            name=message.name,
            full_name=message.full_name,
            ue_name=ue_name,
            fields=fields,
            nested_messages=nested_messages,
            nested_enums=nested_enums,
            oneofs=oneofs,
            source=message,
        )

    def _convert_oneof(
        self,
        oneof: model.Oneof,
        field_map: Dict[int, UEField],
        message_ue_name: str,
    ) -> UEOneofWrapper:
        ue_name = f"{message_ue_name}{self._to_pascal_case(oneof.name)}Oneof"
        cases: List[UEOneofCase] = []
        for field in oneof.fields:
            ue_field = field_map[id(field)]
            case_name = f"{ue_name}{self._to_pascal_case(field.name)}Case"
            cases.append(UEOneofCase(name=field.name, ue_case_name=case_name, field=ue_field))

        return UEOneofWrapper(
            name=oneof.name,
            full_name=oneof.full_name,
            ue_name=ue_name,
            cases=cases,
            source=oneof,
        )

    def _convert_field(self, field: model.Field) -> UEField:
        if field.kind is model.FieldKind.MAP:
            base_type, key_type, value_type = self._map_field_types(field)
            ue_type = base_type
            container = self._map_wrapper
            is_optional = False
            is_repeated = False
            is_map = True
        else:
            base_type = self._base_type_for_field(field)
            is_map = False
            key_type = None
            value_type = None
            is_repeated = field.cardinality is model.FieldCardinality.REPEATED
            is_optional = (
                field.cardinality is model.FieldCardinality.OPTIONAL and field.oneof is None
            )
            container = None
            ue_type = base_type
            if is_repeated:
                ue_type = f"{self._array_wrapper}<{base_type}>"
                container = self._array_wrapper
            elif is_optional:
                ue_type = f"{self._optional_wrapper}<{base_type}>"
                container = self._optional_wrapper

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
            container=container,
            map_key_type=key_type,
            map_value_type=value_type,
            oneof_group=field.oneof,
            json_name=field.json_name,
            default_value=field.default_value,
            source=field,
        )

    def _base_type_for_field(self, field: model.Field) -> str:
        if field.kind is model.FieldKind.SCALAR:
            if not field.scalar:
                raise ValueError(f"Scalar field '{field.name}' does not provide a scalar name")
            mapped = self._SCALAR_MAPPING.get(field.scalar)
            if mapped is None:
                raise KeyError(f"Unsupported scalar type '{field.scalar}' for field '{field.name}'")
            return mapped

        if field.kind in (model.FieldKind.MESSAGE, model.FieldKind.ENUM):
            return self._lookup_symbol(field.resolved_type, field.type_name)

        raise ValueError(f"Unsupported field kind '{field.kind}' for base type resolution")

    def _map_field_types(self, field: model.Field) -> Tuple[str, str, str]:
        if field.map_entry is None:
            raise ValueError(f"Map field '{field.name}' is missing map entry metadata")

        key_type = self._map_entry_part_type(
            field.map_entry.key_kind,
            field.map_entry.key_scalar,
            field.map_entry.key_resolved_type,
            field.map_entry.key_type_name,
            position="key",
        )
        value_type = self._map_entry_part_type(
            field.map_entry.value_kind,
            field.map_entry.value_scalar,
            field.map_entry.value_resolved_type,
            field.map_entry.value_type_name,
            position="value",
        )
        map_type = f"{self._map_wrapper}<{key_type}, {value_type}>"
        return map_type, key_type, value_type

    def _map_entry_part_type(
        self,
        kind: model.FieldKind,
        scalar: Optional[str],
        resolved: Optional[model.ProtoType],
        type_name: Optional[str],
        *,
        position: str,
    ) -> str:
        if kind is model.FieldKind.SCALAR:
            if scalar is None:
                raise ValueError(f"Map {position} is scalar but scalar name is missing")
            mapped = self._SCALAR_MAPPING.get(scalar)
            if mapped is None:
                raise KeyError(f"Unsupported scalar map {position} type '{scalar}'")
            return mapped
        if kind in (model.FieldKind.MESSAGE, model.FieldKind.ENUM):
            return self._lookup_symbol(resolved, type_name)
        raise ValueError(f"Unsupported map {position} kind '{kind}'")

