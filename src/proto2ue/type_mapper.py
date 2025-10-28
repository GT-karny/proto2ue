"""Mapping utilities to transform protobuf model types into UE-friendly dataclasses."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import re
from typing import Dict, Iterable, List, Optional, Tuple

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
    blueprint_type: bool = True
    specifiers: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    category: Optional[str] = None
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
    blueprint_exposed: bool = True
    blueprint_read_only: bool = False
    uproperty_specifiers: List[str] = field(default_factory=list)
    uproperty_metadata: Dict[str, str] = field(default_factory=dict)
    category: Optional[str] = None
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
    blueprint_type: bool = True
    struct_specifiers: List[str] = field(default_factory=list)
    struct_metadata: Dict[str, str] = field(default_factory=dict)
    category: Optional[str] = None
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

    _RESERVED_SYMBOLS = {
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
    }

    _COLLISION_INSERT = "Proto"

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

    def register_files(self, proto_files: Iterable[model.ProtoFile]) -> None:
        """Register symbols for the provided proto files."""

        for proto_file in proto_files:
            self.register_file(proto_file)

    def register_file(self, proto_file: model.ProtoFile) -> None:
        """Register symbols for a single proto file."""

        with self._package_scope(proto_file.package):
            for enum in proto_file.enums:
                self._register_enum(enum)
            for message in proto_file.messages:
                self._register_message(message)

    def map_file(self, proto_file: model.ProtoFile) -> UEProtoFile:
        """Convert a :class:`model.ProtoFile` into :class:`UEProtoFile`."""

        self.register_file(proto_file)

        with self._package_scope(proto_file.package):
            messages = [self._convert_message(message) for message in proto_file.messages]
            enums = [self._convert_enum(enum) for enum in proto_file.enums]

        return UEProtoFile(
            name=proto_file.name,
            package=proto_file.package,
            messages=messages,
            enums=enums,
            source=proto_file,
        )

    @contextmanager
    def _package_scope(self, package: Optional[str]):
        previous = self._package
        self._package = package
        try:
            yield
        finally:
            self._package = previous

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
        existing = self._symbol_table.get(full_name)
        if existing is not None:
            return existing.ue_name
        relative_path = self._relative_symbol_path(full_name)
        pascal_segments = [self._to_pascal_case(segment) for segment in relative_path]
        suffix = "".join(pascal_segments)
        return self._make_unique_type_name(prefix, suffix)

    def _make_unique_type_name(self, prefix: str, suffix: str) -> str:
        candidate = prefix + suffix
        if self._is_name_available(candidate):
            return candidate

        base_suffix = f"{self._COLLISION_INSERT}{suffix}" if suffix else self._COLLISION_INSERT
        attempt = 1
        while True:
            adjusted_suffix = base_suffix if attempt == 1 else f"{base_suffix}{attempt - 1}"
            candidate = prefix + adjusted_suffix
            if self._is_name_available(candidate):
                return candidate
            attempt += 1

    def _is_name_available(self, name: str) -> bool:
        if name in self._RESERVED_SYMBOLS:
            return False
        return all(symbol.ue_name != name for symbol in self._symbol_table.values())

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
        unreal_options = self._extract_unreal_options(enum.options)
        blueprint_type = self._as_bool(unreal_options.get("blueprint_type"), default=True)
        specifiers = self._as_str_list(unreal_options.get("specifiers"))
        metadata = self._as_str_dict(unreal_options.get("meta"))
        category = self._as_optional_str(unreal_options.get("category"))

        values = [
            UEEnumValue(name=value.name, number=value.number, source=value)
            for value in enum.values
        ]
        return UEEnum(
            name=enum.name,
            full_name=enum.full_name,
            ue_name=ue_name,
            values=values,
            blueprint_type=blueprint_type,
            specifiers=specifiers,
            metadata=metadata,
            category=category,
            source=enum,
        )

    def _convert_message(self, message: model.Message) -> UEMessage:
        ue_name = self._lookup_symbol(message, message.full_name)

        unreal_options = self._extract_unreal_options(message.options)
        blueprint_type = self._as_bool(unreal_options.get("blueprint_type"), default=True)
        struct_specifiers = self._as_str_list(unreal_options.get("struct_specifiers"))
        struct_metadata = self._as_str_dict(unreal_options.get("meta"))
        category = self._as_optional_str(unreal_options.get("category"))

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
            blueprint_type=blueprint_type,
            struct_specifiers=struct_specifiers,
            struct_metadata=struct_metadata,
            category=category,
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
        unreal_options = self._extract_unreal_options(field.options)
        blueprint_exposed = self._as_bool(unreal_options.get("blueprint_exposed"), default=True)
        blueprint_read_only = self._as_bool(unreal_options.get("blueprint_read_only"), default=False)
        uproperty_specifiers = self._as_str_list(unreal_options.get("specifiers"))
        uproperty_metadata = self._as_str_dict(unreal_options.get("meta"))
        category = self._as_optional_str(unreal_options.get("category"))

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
            blueprint_exposed=blueprint_exposed,
            blueprint_read_only=blueprint_read_only,
            uproperty_specifiers=uproperty_specifiers,
            uproperty_metadata=uproperty_metadata,
            category=category,
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

    # Metadata helpers -----------------------------------------------------
    def _extract_unreal_options(self, options: Optional[dict]) -> Dict[str, object]:
        if not isinstance(options, dict):
            return {}
        unreal = options.get("unreal")
        if isinstance(unreal, dict):
            return unreal
        return {}

    def _as_bool(self, value: object, *, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "on"}:
                return True
            if lowered in {"false", "0", "no", "off"}:
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        return default

    def _as_optional_str(self, value: object) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return str(value)

    def _as_str_list(self, value: object) -> List[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            result: List[str] = []
            for item in value:
                if item is None:
                    continue
                stringified = str(item)
                if stringified:
                    result.append(stringified)
            return result
        stringified = str(value)
        return [stringified] if stringified else []

    def _as_str_dict(self, value: object) -> Dict[str, str]:
        if not isinstance(value, dict):
            return {}
        result: Dict[str, str] = {}
        for key, raw_value in value.items():
            if key is None:
                continue
            str_key = str(key)
            if not str_key:
                continue
            if raw_value is None:
                continue
            result[str_key] = str(raw_value)
        return result

