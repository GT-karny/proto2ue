from __future__ import annotations

"""Command-line helpers for generating converter sources."""

import argparse
from pathlib import Path
from typing import List, Sequence

from google.protobuf import descriptor_pb2
from google.protobuf.compiler import plugin_pb2

from proto2ue.codegen.converters import ConvertersTemplate, converter_output_path
from proto2ue.descriptor_loader import DescriptorLoader
from proto2ue.type_mapper import TypeMapper


def _build_request(
    descriptor_set: descriptor_pb2.FileDescriptorSet, targets: Sequence[str] | None
) -> plugin_pb2.CodeGeneratorRequest:
    request = plugin_pb2.CodeGeneratorRequest()
    request.proto_file.extend(descriptor_set.file)

    if targets:
        request.file_to_generate.extend(targets)
    else:
        request.file_to_generate.extend(file_proto.name for file_proto in descriptor_set.file)

    return request


def _ensure_targets(
    request: plugin_pb2.CodeGeneratorRequest,
    explicit_targets: Sequence[str] | None,
) -> List[str]:
    if explicit_targets:
        return list(explicit_targets)

    if request.file_to_generate:
        return list(request.file_to_generate)

    return [file_proto.name for file_proto in request.proto_file]


def generate_converters(
    descriptor_set_path: Path | str,
    targets: Sequence[str] | None,
    output_dir: Path | str,
) -> List[Path]:
    """Generate converter files for the given targets.

    Parameters
    ----------
    descriptor_set_path:
        Path to a serialized :class:`~google.protobuf.descriptor_pb2.FileDescriptorSet`.
    targets:
        Proto filenames (as understood by ``protoc``) to generate. ``None`` means "all".
    output_dir:
        Directory that will receive the ``_proto2ue_converters.{h,cpp}`` files.
    """

    descriptor_set_path = Path(descriptor_set_path)
    output_dir = Path(output_dir)

    descriptor_set = descriptor_pb2.FileDescriptorSet()
    descriptor_set.ParseFromString(descriptor_set_path.read_bytes())

    request = _build_request(descriptor_set, targets)

    loader = DescriptorLoader(request)
    loader.load()

    type_mapper = TypeMapper()
    type_mapper.register_files(loader.files.values())

    generated_paths: List[Path] = []
    resolved_targets = _ensure_targets(request, targets)

    for proto_name in resolved_targets:
        ue_file = type_mapper.map_file(loader.get_file(proto_name))
        template = ConvertersTemplate(ue_file)
        rendered = template.render()

        header_rel = converter_output_path(ue_file.name, "_proto2ue_converters.h")
        source_rel = converter_output_path(ue_file.name, "_proto2ue_converters.cpp")
        header_path = output_dir / Path(str(header_rel))
        source_path = output_dir / Path(str(source_rel))
        header_path.parent.mkdir(parents=True, exist_ok=True)
        header_path.write_text(rendered.header)
        source_path.write_text(rendered.source)

        generated_paths.extend([header_path, source_path])

    return generated_paths


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate _proto2ue_converters.{h,cpp} files from a descriptor set produced by protoc."
        )
    )
    parser.add_argument(
        "descriptor_set",
        type=Path,
        help="Path to a serialized FileDescriptorSet (output of protoc --descriptor_set_out)",
    )
    parser.add_argument(
        "--proto",
        dest="protos",
        action="append",
        help=(
            "Proto file to generate (relative to the descriptor). Repeat for multiple files. "
            "Defaults to all entries in the descriptor set."
        ),
    )
    parser.add_argument(
        "--out",
        dest="output",
        required=True,
        type=Path,
        help="Directory to write the generated converter sources to",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point used by ``python -m proto2ue.tools.converter``."""

    parser = _build_argument_parser()
    args = parser.parse_args(argv)

    generated_paths = generate_converters(args.descriptor_set, args.protos, args.output)

    for path in generated_paths:
        print(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
