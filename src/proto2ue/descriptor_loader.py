from __future__ import annotations

"""Utilities to convert CodeGeneratorRequest payloads into model dataclasses."""

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, MutableMapping, Optional, Tuple

from google.protobuf import json_format
from google.protobuf.compiler import plugin_pb2
from google.protobuf import descriptor_pb2
from google.protobuf.message import Message

from . import model


OptionDict = Dict[str, object]
OptionValidator = Callable[["OptionContext", OptionDict], None]


@dataclass(frozen=True, slots=True)
class OptionContext:
    """Describes the location of protobuf options for validation hooks."""

    element_type: str
    file_name: str
    full_name: Optional[str] = None
    field_name: Optional[str] = None


class DescriptorLoader:
    """Load FileDescriptorProto messages into higher level dataclasses."""

    def __init__(
        self,
        request: plugin_pb2.CodeGeneratorRequest,
        *,
        option_validator: Optional[OptionValidator] = None,
    ) -> None:
        self._request = request
        self._option_validator = option_validator
        self._loaded_files: MutableMapping[str, model.ProtoFile] = {}
        self._type_index: Dict[str, model.ProtoType] = {}
        self._pending_field_resolutions: List[Tuple[model.Field, str]] = []
        self._pending_map_resolutions: List[Tuple[model.MapEntry, str, str]] = []
        self._map_entry_descriptors: Dict[str, descriptor_pb2.DescriptorProto] = {}
        self._loaded = False

    @property
    def files(self) -> MutableMapping[str, model.ProtoFile]:
        """Mapping of file name to :class:`ProtoFile` after :meth:`load`."""

        self.load()
        return self._loaded_files

    @property
    def files_to_generate(self) -> List[str]:
        """Return the list of files requested for generation."""

        return list(self._request.file_to_generate)

    def get_file(self, name: str) -> model.ProtoFile:
        """Return a loaded :class:`ProtoFile` by name."""

        self.load()
        return self._loaded_files[name]

    def load(self, file_names: Optional[Iterable[str]] = None) -> MutableMapping[str, model.ProtoFile]:
        """Load requested files and return the mapping of filenames to :class:`ProtoFile`.

        If ``file_names`` is ``None`` all files present in the request are loaded.
        Subsequent calls return cached results.
        """

        if self._loaded:
            if file_names is None:
                return self._loaded_files
            return {name: self._loaded_files[name] for name in file_names}

        for file_proto in self._request.proto_file:
            proto_file = self._convert_file(file_proto)
            self._loaded_files[file_proto.name] = proto_file

        self._resolve_type_references()
        self._loaded = True

        if file_names is None:
            return self._loaded_files

        missing = sorted(name for name in file_names if name not in self._loaded_files)
        if missing:
            raise KeyError(f"Descriptor(s) not found in request: {', '.join(missing)}")
        return {name: self._loaded_files[name] for name in file_names}

    def _convert_file(
        self,
        file_proto: descriptor_pb2.FileDescriptorProto,
    ) -> model.ProtoFile:
        package = file_proto.package or None
        options = self._normalize_options(
            file_proto.options,
            OptionContext(element_type="file", file_name=file_proto.name, full_name=package),
        )
        dependencies = list(file_proto.dependency)
        public_dependencies = [file_proto.dependency[i] for i in file_proto.public_dependency]

        proto_file = model.ProtoFile(
            name=file_proto.name,
            package=package,
            dependencies=dependencies,
            public_dependencies=public_dependencies,
            options=options,
        )

        for enum_proto in file_proto.enum_type:
            enum = self._convert_enum(enum_proto, file_proto, [])
            proto_file.enums.append(enum)

        for message_proto in file_proto.message_type:
            message = self._convert_message(message_proto, file_proto, [])
            proto_file.messages.append(message)

        for dependency in proto_file.dependencies:
            if dependency not in {fp.name for fp in self._request.proto_file}:
                raise KeyError(
                    f"Unresolved dependency '{dependency}' referenced by {file_proto.name}"
                )

        return proto_file

    def _convert_enum(
        self,
        enum_proto: descriptor_pb2.EnumDescriptorProto,
        file_proto: descriptor_pb2.FileDescriptorProto,
        parents: List[str],
    ) -> model.Enum:
        full_name = self._qualify_name(file_proto.package, parents, enum_proto.name)
        options = self._normalize_options(
            enum_proto.options,
            OptionContext(
                element_type="enum",
                file_name=file_proto.name,
                full_name=full_name,
            ),
        )
        enum = model.Enum(name=enum_proto.name, full_name=full_name, options=options)
        self._register_type(full_name, enum)

        for value_proto in enum_proto.value:
            value_context = OptionContext(
                element_type="enum_value",
                file_name=file_proto.name,
                full_name=full_name,
                field_name=value_proto.name,
            )
            value_options = self._normalize_options(value_proto.options, value_context)
            enum_value = model.EnumValue(
                name=value_proto.name,
                number=value_proto.number,
                options=value_options,
            )
            enum.values.append(enum_value)

        return enum

    def _convert_message(
        self,
        message_proto: descriptor_pb2.DescriptorProto,
        file_proto: descriptor_pb2.FileDescriptorProto,
        parents: List[str],
    ) -> model.Message:
        full_name = self._qualify_name(file_proto.package, parents, message_proto.name)
        options = self._normalize_options(
            message_proto.options,
            OptionContext(
                element_type="message",
                file_name=file_proto.name,
                full_name=full_name,
            ),
        )
        message = model.Message(
            name=message_proto.name,
            full_name=full_name,
            options=options,
            reserved_names=list(message_proto.reserved_name),
            reserved_ranges=[(r.start, r.end) for r in message_proto.reserved_range],
            extension_ranges=[(r.start, r.end) for r in message_proto.extension_range],
        )
        self._register_type(full_name, message)

        parents_chain = parents + [message_proto.name]

        for idx, oneof_proto in enumerate(message_proto.oneof_decl):
            oneof_full_name = f"{full_name}.{oneof_proto.name}"
            oneof_options = self._normalize_options(
                oneof_proto.options,
                OptionContext(
                    element_type="oneof",
                    file_name=file_proto.name,
                    full_name=oneof_full_name,
                ),
            )
            oneof = model.Oneof(name=oneof_proto.name, full_name=oneof_full_name, options=oneof_options)
            message.oneofs.append(oneof)

        for nested_proto in message_proto.nested_type:
            nested_full_name = self._qualify_name(file_proto.package, parents_chain, nested_proto.name)
            if nested_proto.options.map_entry:
                self._map_entry_descriptors[nested_full_name] = nested_proto
                continue
            nested_message = self._convert_message(nested_proto, file_proto, parents_chain)
            message.nested_messages.append(nested_message)

        for enum_proto in message_proto.enum_type:
            nested_enum = self._convert_enum(enum_proto, file_proto, parents_chain)
            message.nested_enums.append(nested_enum)

        for field_proto in message_proto.field:
            field = self._convert_field(field_proto, message, file_proto.name)
            message.fields.append(field)

        for field in message.fields:
            if field.oneof_index is not None:
                message.oneofs[field.oneof_index].fields.append(field)

        return message

    def _convert_field(
        self,
        field_proto: descriptor_pb2.FieldDescriptorProto,
        message: model.Message,
        file_name: str,
    ) -> model.Field:
        label = field_proto.label
        cardinality = {
            descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL: model.FieldCardinality.OPTIONAL,
            descriptor_pb2.FieldDescriptorProto.LABEL_REQUIRED: model.FieldCardinality.REQUIRED,
            descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED: model.FieldCardinality.REPEATED,
        }[label]

        kind, scalar, type_name = self._classify_field_type(field_proto)

        map_entry = None
        if (
            kind is model.FieldKind.MESSAGE
            and cardinality is model.FieldCardinality.REPEATED
            and type_name in self._map_entry_descriptors
        ):
            map_entry = self._build_map_entry(type_name)
            kind = model.FieldKind.MAP
            scalar = None

        normalized_type_name = type_name if type_name else None
        context = OptionContext(
            element_type="field",
            file_name=file_name,
            full_name=message.full_name,
            field_name=field_proto.name,
        )
        options = self._normalize_options(field_proto.options, context)
        json_name = field_proto.json_name or None
        default_value = field_proto.default_value or None
        oneof_index = field_proto.oneof_index if field_proto.HasField("oneof_index") else None
        oneof_name = message.oneofs[oneof_index].name if oneof_index is not None else None

        field = model.Field(
            name=field_proto.name,
            number=field_proto.number,
            cardinality=cardinality,
            kind=kind,
            scalar=scalar,
            type_name=normalized_type_name,
            map_entry=map_entry,
            default_value=default_value,
            json_name=json_name,
            oneof=oneof_name,
            oneof_index=oneof_index,
            proto3_optional=field_proto.proto3_optional,
            options=options,
        )

        if field_proto.options and field_proto.options.HasField("packed"):
            field.packed = field_proto.options.packed

        if field.kind is model.FieldKind.MESSAGE and field.type_name:
            self._pending_field_resolutions.append((field, field.type_name))
        elif field.kind is model.FieldKind.ENUM and field.type_name:
            self._pending_field_resolutions.append((field, field.type_name))

        if field.map_entry:
            if (
                field.map_entry.value_kind in (model.FieldKind.MESSAGE, model.FieldKind.ENUM)
                and field.map_entry.value_type_name
            ):
                self._pending_map_resolutions.append(
                    (field.map_entry, field.map_entry.value_type_name, "value")
                )
            if (
                field.map_entry.key_kind in (model.FieldKind.MESSAGE, model.FieldKind.ENUM)
                and field.map_entry.key_type_name
            ):
                self._pending_map_resolutions.append(
                    (field.map_entry, field.map_entry.key_type_name, "key")
                )

        return field

    def _build_map_entry(self, type_name: str) -> model.MapEntry:
        descriptor = self._map_entry_descriptors[type_name]
        key_field = descriptor.field[0]
        value_field = descriptor.field[1]

        key_kind, key_scalar, key_type_name = self._classify_field_type(key_field)
        value_kind, value_scalar, value_type_name = self._classify_field_type(value_field)

        map_entry = model.MapEntry(
            key_kind=key_kind,
            key_scalar=key_scalar,
            key_type_name=key_type_name,
            value_kind=value_kind,
            value_scalar=value_scalar,
            value_type_name=value_type_name,
        )
        return map_entry

    def _classify_field_type(
        self, field_proto: descriptor_pb2.FieldDescriptorProto
    ) -> Tuple[model.FieldKind, Optional[str], Optional[str]]:
        field_type = field_proto.type
        if field_type in _SCALAR_TYPE_NAMES:
            return model.FieldKind.SCALAR, _SCALAR_TYPE_NAMES[field_type], None
        if field_type == descriptor_pb2.FieldDescriptorProto.TYPE_ENUM:
            return model.FieldKind.ENUM, None, self._normalize_type_name(field_proto.type_name)
        if field_type == descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE:
            return model.FieldKind.MESSAGE, None, self._normalize_type_name(field_proto.type_name)
        raise ValueError(f"Unsupported field type: {field_type}")

    def _normalize_type_name(self, type_name: str) -> str:
        if not type_name:
            return type_name
        return type_name[1:] if type_name.startswith(".") else type_name

    def _register_type(self, full_name: str, obj: model.ProtoType) -> None:
        self._type_index[full_name] = obj

    def _qualify_name(
        self, package: Optional[str], parents: List[str], name: str
    ) -> str:
        segments: List[str] = []
        if package:
            segments.append(package)
        segments.extend(parents)
        segments.append(name)
        return ".".join(segment for segment in segments if segment)

    def _normalize_options(
        self,
        options: Optional[Message],
        context: OptionContext,
    ) -> OptionDict:
        if options is None:
            normalized: OptionDict = {}
        else:
            normalized = self._message_to_dict(options)
        if self._option_validator is not None:
            self._option_validator(context, normalized)
        return normalized

    def _message_to_dict(self, message: Message) -> OptionDict:
        """Convert a protobuf message to a dictionary handling protobuf version differences."""

        kwargs = {
            "preserving_proto_field_name": True,
            "including_default_value_fields": False,
        }
        try:
            return json_format.MessageToDict(message, **kwargs)
        except TypeError:
            kwargs.pop("including_default_value_fields")
            return json_format.MessageToDict(message, **kwargs)

    def _resolve_type_references(self) -> None:
        for field, type_name in self._pending_field_resolutions:
            resolved = self._type_index.get(type_name)
            if resolved is None:
                raise KeyError(f"Unable to resolve type reference '{type_name}' for field '{field.name}'")
            field.resolved_type = resolved

        for map_entry, type_name, position in self._pending_map_resolutions:
            resolved = self._type_index.get(type_name)
            if resolved is None:
                raise KeyError(f"Unable to resolve type reference '{type_name}' for map {position}")
            if position == "key":
                map_entry.key_resolved_type = resolved
            else:
                map_entry.value_resolved_type = resolved


_SCALAR_TYPE_NAMES: Dict[int, str] = {
    descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE: "double",
    descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT: "float",
    descriptor_pb2.FieldDescriptorProto.TYPE_INT64: "int64",
    descriptor_pb2.FieldDescriptorProto.TYPE_UINT64: "uint64",
    descriptor_pb2.FieldDescriptorProto.TYPE_INT32: "int32",
    descriptor_pb2.FieldDescriptorProto.TYPE_FIXED64: "fixed64",
    descriptor_pb2.FieldDescriptorProto.TYPE_FIXED32: "fixed32",
    descriptor_pb2.FieldDescriptorProto.TYPE_BOOL: "bool",
    descriptor_pb2.FieldDescriptorProto.TYPE_STRING: "string",
    descriptor_pb2.FieldDescriptorProto.TYPE_BYTES: "bytes",
    descriptor_pb2.FieldDescriptorProto.TYPE_UINT32: "uint32",
    descriptor_pb2.FieldDescriptorProto.TYPE_SFIXED32: "sfixed32",
    descriptor_pb2.FieldDescriptorProto.TYPE_SFIXED64: "sfixed64",
    descriptor_pb2.FieldDescriptorProto.TYPE_SINT32: "sint32",
    descriptor_pb2.FieldDescriptorProto.TYPE_SINT64: "sint64",
}

