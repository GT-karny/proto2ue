from __future__ import annotations

import pytest

pytest.importorskip("google.protobuf")

from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2

from proto2ue.descriptor_loader import DescriptorLoader, OptionContext
from proto2ue import model


def _build_request() -> plugin_pb2.CodeGeneratorRequest:
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = "example.proto"
    file_proto.package = "example.pkg"
    file_proto.options.java_multiple_files = True

    color_enum = file_proto.enum_type.add()
    color_enum.name = "Color"
    red_value = color_enum.value.add()
    red_value.name = "COLOR_RED"
    red_value.number = 1

    thing_msg = file_proto.message_type.add()
    thing_msg.name = "Thing"
    thing_msg.options.deprecated = True

    map_entry = thing_msg.nested_type.add()
    map_entry.name = "LabelsEntry"
    map_entry.options.map_entry = True
    map_key = map_entry.field.add()
    map_key.name = "key"
    map_key.number = 1
    map_key.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    map_key.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    map_value = map_entry.field.add()
    map_value.name = "value"
    map_value.number = 2
    map_value.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    map_value.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    map_value.type_name = ".example.pkg.Meta"

    labels_field = thing_msg.field.add()
    labels_field.name = "labels"
    labels_field.number = 1
    labels_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    labels_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    labels_field.type_name = ".example.pkg.Thing.LabelsEntry"

    color_field = thing_msg.field.add()
    color_field.name = "color"
    color_field.number = 2
    color_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    color_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_ENUM
    color_field.type_name = ".example.pkg.Color"
    color_field.options.deprecated = True

    thing_oneof = thing_msg.oneof_decl.add()
    thing_oneof.name = "selection"

    name_field = thing_msg.field.add()
    name_field.name = "name"
    name_field.number = 3
    name_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    name_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    name_field.oneof_index = 0
    name_field.proto3_optional = True

    meta_message = file_proto.message_type.add()
    meta_message.name = "Meta"

    meta_field = thing_msg.field.add()
    meta_field.name = "meta"
    meta_field.number = 4
    meta_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    meta_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    meta_field.type_name = ".example.pkg.Meta"

    request = plugin_pb2.CodeGeneratorRequest()
    request.file_to_generate.append("example.proto")
    request.proto_file.append(file_proto)
    return request


def test_descriptor_loader_builds_intermediate_model() -> None:
    request = _build_request()
    loader = DescriptorLoader(request)
    files = loader.load()

    assert "example.proto" in files
    proto_file = files["example.proto"]
    assert proto_file.package == "example.pkg"
    assert proto_file.options["java_multiple_files"] is True

    assert len(proto_file.messages) == 2
    thing, meta = proto_file.messages
    assert thing.full_name == "example.pkg.Thing"
    assert meta.full_name == "example.pkg.Meta"

    assert thing.options["deprecated"] is True
    assert len(thing.fields) == 4

    labels_field = thing.fields[0]
    assert labels_field.kind is model.FieldKind.MAP
    assert labels_field.map_entry is not None
    assert labels_field.map_entry.key_kind is model.FieldKind.SCALAR
    assert labels_field.map_entry.key_scalar == "string"
    assert labels_field.map_entry.value_kind is model.FieldKind.MESSAGE
    assert labels_field.map_entry.value_type_name == "example.pkg.Meta"
    assert labels_field.map_entry.value_resolved_type is meta

    color_field = thing.fields[1]
    assert color_field.kind is model.FieldKind.ENUM
    assert isinstance(color_field.resolved_type, model.Enum)
    assert color_field.resolved_type.name == "Color"
    assert color_field.options["deprecated"] is True

    name_field = thing.fields[2]
    assert name_field.oneof == "selection"
    assert name_field.proto3_optional is True

    meta_field = thing.fields[3]
    assert meta_field.kind is model.FieldKind.MESSAGE
    assert meta_field.resolved_type is meta

    assert len(thing.oneofs) == 1
    assert thing.oneofs[0].fields[0] is name_field

    assert len(proto_file.enums) == 1
    enum = proto_file.enums[0]
    assert enum.full_name == "example.pkg.Color"
    assert enum.values[0].name == "COLOR_RED"


def test_option_validator_receives_contexts() -> None:
    request = _build_request()
    seen: list[tuple[str, str | None, str | None]] = []

    def validator(context: OptionContext, options: dict[str, object]) -> None:
        if options:
            seen.append((context.element_type, context.full_name, context.field_name))

    loader = DescriptorLoader(request, option_validator=validator)
    loader.load()

    assert ("file", "example.pkg", None) in seen
    assert ("message", "example.pkg.Thing", None) in seen
    assert ("field", "example.pkg.Thing", "color") in seen
