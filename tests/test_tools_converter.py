from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("google.protobuf")

from google.protobuf import descriptor_pb2

from proto2ue.codegen.converters import converter_output_path
from proto2ue.tools import converter


def _write_descriptor(tmp_path: Path) -> Path:
    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = "example/person.proto"
    file_proto.package = "example"
    file_proto.syntax = "proto2"

    person_message = file_proto.message_type.add()
    person_message.name = "Person"

    id_field = person_message.field.add()
    id_field.name = "id"
    id_field.number = 1
    id_field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    id_field.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32

    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.file.append(file_proto)

    descriptor_path = tmp_path / "bundle.pb"
    descriptor_path.write_bytes(descriptor_set.SerializeToString())
    return descriptor_path


def test_generate_converters_creates_outputs(tmp_path: Path) -> None:
    descriptor_path = _write_descriptor(tmp_path)
    output_dir = tmp_path / "out"

    generated = converter.generate_converters(descriptor_path, ["example/person.proto"], output_dir)

    header_rel = converter_output_path("example/person.proto", "_proto2ue_converters.h")
    source_rel = converter_output_path("example/person.proto", "_proto2ue_converters.cpp")
    header_path = output_dir / Path(str(header_rel))
    source_path = output_dir / Path(str(source_rel))

    assert header_path in generated
    assert source_path in generated
    assert header_path.exists()
    assert source_path.exists()

    header_text = header_path.read_text()
    assert "Generated conversion helpers by proto2ue." in header_text


def test_main_defaults_to_all_targets(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    descriptor_path = _write_descriptor(tmp_path)
    output_dir = tmp_path / "generated"

    exit_code = converter.main([str(descriptor_path), "--out", str(output_dir)])

    assert exit_code == 0

    captured = capsys.readouterr()
    header_rel = converter_output_path("example/person.proto", "_proto2ue_converters.h")
    source_rel = converter_output_path("example/person.proto", "_proto2ue_converters.cpp")
    assert str(header_rel) in captured.out
    assert str(source_rel) in captured.out

    assert (output_dir / Path(str(header_rel))).exists()
    assert (output_dir / Path(str(source_rel))).exists()
