from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("google.protobuf")

from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2

from proto2ue.codegen import sanitize_generated_filename
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


def _build_unsigned_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    file_proto = request.proto_file.add()
    file_proto.name = "example/unsigned.proto"
    file_proto.package = "example"

    message = file_proto.message_type.add()
    message.name = "Unsigned"

    count_field = message.field.add()
    count_field.name = "count"
    count_field.number = 1
    count_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    count_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT32

    request.file_to_generate.append("example/unsigned.proto")
    return request


def test_default_renderer_outputs_golden_files() -> None:
    request = _build_sample_request()
    response = generate_code(request)

    files = {file.name: file.content for file in response.file}
    person_header = sanitize_generated_filename("example/person.proto2ue.h")
    person_source = sanitize_generated_filename("example/person.proto2ue.cpp")
    assert set(files) == {person_header, person_source}

    header_output = files[person_header]
    source_output = files[person_source]

    assert "UE_NAMESPACE_BEGIN(" not in header_output
    assert "UE_NAMESPACE_END(" not in header_output
    assert "UE_NAMESPACE_BEGIN(" not in source_output
    assert "UE_NAMESPACE_END(" not in source_output

    golden_dir = Path(__file__).parent / "golden"
    header_golden = (
        golden_dir / "example" / person_header.rsplit("/", 1)[-1]
    ).read_text()
    source_golden = (
        golden_dir / "example" / person_source.rsplit("/", 1)[-1]
    ).read_text()

    assert header_output == header_golden
    assert source_output == source_golden


def test_renderer_splits_namespace_segments() -> None:
    request = plugin_pb2.CodeGeneratorRequest()
    file_proto = request.proto_file.add()
    file_proto.name = "demo/example.proto"
    file_proto.package = "demo.example"

    message = file_proto.message_type.add()
    message.name = "Widget"

    request.file_to_generate.append("demo/example.proto")

    response = generate_code(request)
    files = {file.name: file.content for file in response.file}

    example_header = sanitize_generated_filename("demo/example.proto2ue.h")
    example_source = sanitize_generated_filename("demo/example.proto2ue.cpp")
    header_output = files[example_header]
    source_output = files[example_source]

    assert "UE_NAMESPACE_BEGIN(" not in header_output
    assert "UE_NAMESPACE_END(" not in header_output
    assert "UE_NAMESPACE_BEGIN(" not in source_output
    assert "UE_NAMESPACE_END(" not in source_output

    # Ensure the generated identifiers do not contain namespace separators
    assert "RegisterGeneratedTypes_demo_example" in source_output
    assert "RegisterGeneratedTypes_demo/example" not in source_output


def test_renderer_sanitizes_generated_filenames() -> None:
    request = plugin_pb2.CodeGeneratorRequest()

    dependency_proto = request.proto_file.add()
    dependency_proto.name = "demo/dependency.file.proto"
    dependency_proto.package = "demo"
    dependency_message = dependency_proto.message_type.add()
    dependency_message.name = "DependencyMessage"

    file_proto = request.proto_file.add()
    file_proto.name = "demo/widget.config.proto"
    file_proto.package = "demo"
    file_proto.dependency.append("demo/dependency.file.proto")

    widget_message = file_proto.message_type.add()
    widget_message.name = "Widget"
    dep_field = widget_message.field.add()
    dep_field.name = "dependency"
    dep_field.number = 1
    dep_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    dep_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    dep_field.type_name = ".demo.DependencyMessage"

    request.file_to_generate.append("demo/widget.config.proto")

    response = generate_code(request)
    files = {file.name: file.content for file in response.file}

    widget_header = sanitize_generated_filename("demo/widget.config.proto2ue.h")
    widget_source = sanitize_generated_filename("demo/widget.config.proto2ue.cpp")
    dependency_header = sanitize_generated_filename("demo/dependency.file.proto2ue.h")
    expected_names = {widget_header, widget_source}
    assert set(files) == expected_names

    header_output = files[widget_header]
    assert f'#include "{dependency_header}"' in header_output
    assert f'#include "{widget_header[:-2]}.generated.h"' in header_output

    for name in files:
        component = name.rsplit("/", 1)[-1]
        if "." in component:
            base = component[: component.rfind(".")]
        else:
            base = component
        assert base
        assert all(ch.isalnum() or ch == "_" for ch in base)


def test_renderer_disambiguates_colliding_sanitized_filenames() -> None:
    request = plugin_pb2.CodeGeneratorRequest()

    first = request.proto_file.add()
    first.name = "demo/foo-bar.proto"
    first.package = "demo"
    first.message_type.add().name = "Foo"

    second = request.proto_file.add()
    second.name = "demo/foo.bar.proto"
    second.package = "demo"
    second.message_type.add().name = "Bar"

    request.file_to_generate.extend(["demo/foo-bar.proto", "demo/foo.bar.proto"])

    response = generate_code(request)
    files = {file.name for file in response.file}

    first_header = sanitize_generated_filename("demo/foo-bar.proto2ue.h")
    second_header = sanitize_generated_filename("demo/foo.bar.proto2ue.h")
    first_source = sanitize_generated_filename("demo/foo-bar.proto2ue.cpp")
    second_source = sanitize_generated_filename("demo/foo.bar.proto2ue.cpp")

    assert first_header in files
    assert first_source in files
    assert second_header in files
    assert second_source in files

    assert first_header != second_header
    assert first_source != second_source

def test_generate_code_respects_unsigned_blueprint_flag_default() -> None:
    request = _build_unsigned_request()
    response = generate_code(request)

    files = {file.name: file.content for file in response.file}
    unsigned_header = sanitize_generated_filename("example/unsigned.proto2ue.h")
    header_output = files[unsigned_header]

    assert "uint32 Value" in header_output
    assert "FProtoOptionalExampleUnsignedUint32 count" in header_output


def test_generate_code_converts_unsigned_when_flag_enabled() -> None:
    request = _build_unsigned_request()
    request.parameter = "convert_unsigned_for_blueprint=true"
    response = generate_code(request)

    files = {file.name: file.content for file in response.file}
    unsigned_header = sanitize_generated_filename("example/unsigned.proto2ue.h")
    header_output = files[unsigned_header]

    assert "int32 Value" in header_output
    assert "FProtoOptionalExampleUnsignedInt32 count" in header_output


def _build_reserved_collision_request() -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    file_proto = request.proto_file.add()
    file_proto.name = "physics/vector.proto"
    file_proto.package = "physics"

    vector_message = file_proto.message_type.add()
    vector_message.name = "Vector"
    next_field = vector_message.field.add()
    next_field.name = "next"
    next_field.number = 1
    next_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    next_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    next_field.type_name = ".physics.Vector"

    request.file_to_generate.append("physics/vector.proto")
    return request


def test_renderer_handles_reserved_identifier_collision() -> None:
    request = _build_reserved_collision_request()
    response = generate_code(request)

    files = {file.name: file.content for file in response.file}
    vector_header = sanitize_generated_filename("physics/vector.proto2ue.h")
    header_output = files[vector_header]

    assert "struct FProtoVector" in header_output
    assert "struct FProtoOptionalPhysicsVectorFProtoVector" in header_output


def test_renderer_respects_rename_override_parameter() -> None:
    request = _build_reserved_collision_request()
    request.parameter = "rename_overrides=physics.Vector:FPhysicsVector"

    response = generate_code(request)

    files = {file.name: file.content for file in response.file}
    vector_header = sanitize_generated_filename("physics/vector.proto2ue.h")
    header_output = files[vector_header]

    assert "struct FPhysicsVector" in header_output
    assert "struct FProtoOptionalPhysicsVectorFPhysicsVector" in header_output
    assert "struct FProtoVector" not in header_output


def test_renderer_includes_cross_file_dependencies() -> None:
    request = plugin_pb2.CodeGeneratorRequest()

    address_file = request.proto_file.add()
    address_file.name = "common/address.proto"
    address_file.package = "common"

    address_message = address_file.message_type.add()
    address_message.name = "Address"
    line1_field = address_message.field.add()
    line1_field.name = "line1"
    line1_field.number = 1
    line1_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    line1_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING

    person_file = request.proto_file.add()
    person_file.name = "example/person.proto"
    person_file.package = "example"
    person_file.dependency.append("common/address.proto")

    person_message = person_file.message_type.add()
    person_message.name = "Person"
    address_field = person_message.field.add()
    address_field.name = "home_address"
    address_field.number = 1
    address_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    address_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    address_field.type_name = ".common.Address"

    request.file_to_generate.append("example/person.proto")

    response = generate_code(request)
    files = {file.name: file.content for file in response.file}
    person_header = sanitize_generated_filename("example/person.proto2ue.h")
    dependency_header = sanitize_generated_filename("common/address.proto2ue.h")
    header_output = files[person_header]

    dependency_include = f'#include "{dependency_header}"'
    assert dependency_include in header_output
    assert header_output.index(dependency_include) < header_output.index(
        f'#include "{person_header[:-2]}.generated.h"'
    )
