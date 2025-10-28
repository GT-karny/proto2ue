from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("google.protobuf")

from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2

from proto2ue.plugin import generate_code


def _build_sample_request() -> plugin_pb2.CodeGeneratorRequest:
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = "example/person.proto"
    file_proto.package = "example"

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

    # Nested message: Attributes
    attributes_message = person_message.nested_type.add()
    attributes_message.name = "Attributes"
    attribute_field = attributes_message.field.add()
    attribute_field.name = "nickname"
    attribute_field.number = 1
    attribute_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    attribute_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING

    # Map entry message for labels map
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

    # Nested enum for mood
    mood_enum = person_message.enum_type.add()
    mood_enum.name = "Mood"
    mood_enum.value.add(name="MOOD_UNSPECIFIED", number=0)
    mood_enum.value.add(name="MOOD_HAPPY", number=1)

    # Oneof declaration for contact
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
    return request


def test_default_renderer_outputs_golden_files() -> None:
    request = _build_sample_request()
    response = generate_code(request)

    files = {file.name: file.content for file in response.file}
    assert set(files) == {
        "example/person.proto2ue.h",
        "example/person.proto2ue.cpp",
    }

    header_output = files["example/person.proto2ue.h"]
    source_output = files["example/person.proto2ue.cpp"]

    assert "UE_NAMESPACE_BEGIN(example)" in header_output
    assert "UE_NAMESPACE_END(example)" in header_output
    assert "UE_NAMESPACE_BEGIN(example)" in source_output
    assert "UE_NAMESPACE_END(example)" in source_output

    golden_dir = Path(__file__).parent / "golden"
    header_golden = (golden_dir / "example" / "person.proto2ue.h").read_text()
    source_golden = (golden_dir / "example" / "person.proto2ue.cpp").read_text()

    assert header_output == header_golden
    assert source_output == source_golden
