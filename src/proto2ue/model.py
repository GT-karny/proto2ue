from __future__ import annotations

"""Dataclasses representing a protobuf schema in a plugin-friendly format."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class FieldCardinality(str, Enum):
    """Cardinality for message fields."""

    OPTIONAL = "optional"
    REQUIRED = "required"
    REPEATED = "repeated"


class FieldKind(str, Enum):
    """Different underlying kinds for a field."""

    SCALAR = "scalar"
    ENUM = "enum"
    MESSAGE = "message"
    MAP = "map"


@dataclass(slots=True)
class MapEntry:
    """Normalized representation for protobuf map fields."""

    key_kind: FieldKind
    key_scalar: Optional[str] = None
    key_type_name: Optional[str] = None
    value_kind: FieldKind = FieldKind.SCALAR
    value_scalar: Optional[str] = None
    value_type_name: Optional[str] = None
    key_resolved_type: Optional[ProtoType] = None
    value_resolved_type: Optional[ProtoType] = None


@dataclass(slots=True)
class Field:
    """Represents a message field."""

    name: str
    number: int
    cardinality: FieldCardinality
    kind: FieldKind
    scalar: Optional[str] = None
    type_name: Optional[str] = None
    resolved_type: Optional[ProtoType] = None
    map_entry: Optional[MapEntry] = None
    default_value: Optional[str] = None
    json_name: Optional[str] = None
    oneof: Optional[str] = None
    oneof_index: Optional[int] = None
    proto3_optional: bool = False
    packed: Optional[bool] = None
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EnumValue:
    """Represents a value within an enum."""

    name: str
    number: int
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Enum:
    """Represents an enum type."""

    name: str
    full_name: str
    values: List[EnumValue] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Oneof:
    """Represents a oneof declaration."""

    name: str
    full_name: str
    fields: List[Field] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Message:
    """Represents a message type."""

    name: str
    full_name: str
    fields: List[Field] = field(default_factory=list)
    nested_messages: List[Message] = field(default_factory=list)
    nested_enums: List[Enum] = field(default_factory=list)
    oneofs: List[Oneof] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)
    reserved_names: List[str] = field(default_factory=list)
    reserved_ranges: List[tuple[int, int]] = field(default_factory=list)
    extension_ranges: List[tuple[int, int]] = field(default_factory=list)


@dataclass(slots=True)
class ProtoFile:
    """Represents a protobuf file and its declarations."""

    name: str
    package: Optional[str]
    dependencies: List[str] = field(default_factory=list)
    public_dependencies: List[str] = field(default_factory=list)
    messages: List[Message] = field(default_factory=list)
    enums: List[Enum] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)


ProtoType = Message | Enum

