from __future__ import annotations

import pytest

pytest.importorskip("google.protobuf")

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory
from google.protobuf.compiler import plugin_pb2

from proto2ue.codegen.converters import ConversionContext, ConvertersTemplate
from proto2ue.descriptor_loader import DescriptorLoader
from proto2ue.type_mapper import TypeMapper


def _build_sample_components():
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = "example/person.proto"
    file_proto.package = "example"
    file_proto.syntax = "proto2"

    color_enum = file_proto.enum_type.add()
    color_enum.name = "Color"
    color_enum.value.add(name="COLOR_UNSPECIFIED", number=0)
    color_enum.value.add(name="COLOR_RED", number=1)

    meta_message = file_proto.message_type.add()
    meta_message.name = "Meta"
    meta_field = meta_message.field.add()
    meta_field.name = "created_by"
    meta_field.number = 1
    meta_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    meta_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING

    person_message = file_proto.message_type.add()
    person_message.name = "Person"

    attributes_message = person_message.nested_type.add()
    attributes_message.name = "Attributes"
    attribute_field = attributes_message.field.add()
    attribute_field.name = "nickname"
    attribute_field.number = 1
    attribute_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    attribute_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING

    labels_entry = person_message.nested_type.add()
    labels_entry.name = "LabelsEntry"
    labels_entry.options.map_entry = True
    labels_key = labels_entry.field.add()
    labels_key.name = "key"
    labels_key.number = 1
    labels_key.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    labels_key.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    labels_value = labels_entry.field.add()
    labels_value.name = "value"
    labels_value.number = 2
    labels_value.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    labels_value.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    labels_value.type_name = ".example.Meta"

    mood_enum = person_message.enum_type.add()
    mood_enum.name = "Mood"
    mood_enum.value.add(name="MOOD_UNSPECIFIED", number=0)
    mood_enum.value.add(name="MOOD_HAPPY", number=1)

    contact_oneof = person_message.oneof_decl.add()
    contact_oneof.name = "contact"

    id_field = person_message.field.add()
    id_field.name = "id"
    id_field.number = 1
    id_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    id_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32

    scores_field = person_message.field.add()
    scores_field.name = "scores"
    scores_field.number = 2
    scores_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    scores_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT

    labels_field = person_message.field.add()
    labels_field.name = "labels"
    labels_field.number = 3
    labels_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_REPEATED
    labels_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    labels_field.type_name = ".example.Person.LabelsEntry"

    color_field = person_message.field.add()
    color_field.name = "primary_color"
    color_field.number = 4
    color_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    color_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_ENUM
    color_field.type_name = ".example.Color"

    attributes_field = person_message.field.add()
    attributes_field.name = "attributes"
    attributes_field.number = 5
    attributes_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    attributes_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    attributes_field.type_name = ".example.Person.Attributes"

    email_field = person_message.field.add()
    email_field.name = "email"
    email_field.number = 6
    email_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    email_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    email_field.oneof_index = 0

    phone_field = person_message.field.add()
    phone_field.name = "phone"
    phone_field.number = 7
    phone_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    phone_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    phone_field.oneof_index = 0

    mood_field = person_message.field.add()
    mood_field.name = "mood"
    mood_field.number = 8
    mood_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    mood_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_ENUM
    mood_field.type_name = ".example.Person.Mood"

    request = plugin_pb2.CodeGeneratorRequest()
    request.proto_file.append(file_proto)
    request.file_to_generate.append("example/person.proto")

    loader = DescriptorLoader(request)
    loader.load()
    type_mapper = TypeMapper()
    ue_file = type_mapper.map_file(loader.get_file("example/person.proto"))

    pool = descriptor_pool.DescriptorPool()
    pool.Add(file_proto)
    factory = message_factory.MessageFactory(pool)
    person_cls = factory.GetPrototype(pool.FindMessageTypeByName("example.Person"))
    return ue_file, person_cls


def test_python_runtime_round_trip() -> None:
    ue_file, person_cls = _build_sample_components()
    template = ConvertersTemplate(ue_file)
    runtime = template.python_runtime()

    ue_input = {
        "id": {"bIsSet": True, "Value": 42},
        "scores": [1.0, 2.5],
        "labels": {
            "team": {
                "created_by": {"bIsSet": True, "Value": "system"},
            }
        },
        "primary_color": {"bIsSet": True, "Value": 1},
        "attributes": {
            "bIsSet": True,
            "Value": {
                "nickname": {"bIsSet": True, "Value": "Proto"},
            },
        },
        "email": {"bIsSet": True, "Value": ""},
        "phone": {"bIsSet": False, "Value": None},
        "mood": {"bIsSet": True, "Value": 1},
    }

    to_proto_context = ConversionContext()
    proto_message = runtime.to_proto(
        "example.Person", ue_input, person_cls(), to_proto_context
    )
    assert not to_proto_context.has_errors()
    assert proto_message.WhichOneof("contact") == "email"
    assert proto_message.email == ""

    from_proto_context = ConversionContext()
    ue_roundtrip = runtime.from_proto(
        "example.Person", proto_message, from_proto_context
    )
    assert not from_proto_context.has_errors()
    assert ue_roundtrip["email"] == {"bIsSet": True, "Value": ""}
    assert ue_roundtrip["phone"] == {"bIsSet": False, "Value": None}
    assert ue_roundtrip["id"] == {"bIsSet": True, "Value": 42}
    assert ue_roundtrip["mood"] == {"bIsSet": True, "Value": 1}
    assert ue_roundtrip["attributes"] == {
        "bIsSet": True,
        "Value": {"nickname": {"bIsSet": True, "Value": "Proto"}},
    }
    assert ue_roundtrip["labels"]["team"] == {
        "created_by": {"bIsSet": True, "Value": "system"}
    }

    roundtrip_proto = runtime.to_proto(
        "example.Person", ue_roundtrip, person_cls(), ConversionContext()
    )
    assert proto_message.SerializeToString() == roundtrip_proto.SerializeToString()


def test_converters_template_emits_static_class_helpers() -> None:
    ue_file, _ = _build_sample_components()
    template = ConvertersTemplate(ue_file)
    rendered = template.render()

    assert "namespace Proto2UE::Converters" not in rendered.header
    assert "namespace Proto2UE::Converters" not in rendered.source
    assert "Internal::" not in rendered.header
    assert "Internal::" not in rendered.source

    expected_class = "FExampleProtoConv"
    assert f"class {expected_class}" in rendered.header
    assert f"void {expected_class}::ToProto" in rendered.source
    assert f"bool {expected_class}::FromProto" in rendered.source
    assert f"{expected_class}::FConversionContext" in rendered.source
    assert f"{expected_class}::ToProtoBytes" in rendered.source
    assert f"{expected_class}::FromProtoBytes" in rendered.source

    assert '#include "example/person_proto2ue_converters.h"' in rendered.source
    assert '#include "example/person_proto2ue_converters.generated.h"' in rendered.header

