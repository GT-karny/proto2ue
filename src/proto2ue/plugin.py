"""Protocol Buffers compiler plugin entry point for proto2ue."""
from __future__ import annotations

import sys
from typing import Any, Iterable

from google.protobuf.compiler import plugin_pb2

from .codegen import DefaultTemplateRenderer, GeneratedFile, ITemplateRenderer
from .descriptor_loader import DescriptorLoader
from .type_mapper import TypeMapper


def analyze_descriptors(request: plugin_pb2.CodeGeneratorRequest) -> Any:
    """Normalize descriptors into the proto2ue intermediate model."""

    loader = DescriptorLoader(request)
    return loader.load()


def generate_code(
    request: plugin_pb2.CodeGeneratorRequest,
    *,
    renderer: ITemplateRenderer | None = None,
) -> plugin_pb2.CodeGeneratorResponse:
    """Run the proto2ue pipeline and return a populated response message."""

    loader = DescriptorLoader(request)
    loader.load()

    files_to_generate = loader.files_to_generate
    if not files_to_generate:
        files_to_generate = list(loader.files.keys())

    response = plugin_pb2.CodeGeneratorResponse()
    type_mapper = TypeMapper()
    renderer = renderer or DefaultTemplateRenderer()

    for file_name in files_to_generate:
        proto_file = loader.get_file(file_name)
        ue_file = type_mapper.map_file(proto_file)
        generated_files: Iterable[GeneratedFile] = renderer.render(ue_file)
        for generated in generated_files:
            response_file = response.file.add()
            response_file.name = generated.name
            response_file.content = generated.content

    return response


def main() -> None:
    """Execute the protoc plugin workflow."""

    request_payload = sys.stdin.buffer.read()

    request = plugin_pb2.CodeGeneratorRequest()
    if request_payload:
        request.ParseFromString(request_payload)

    response = generate_code(request)
    sys.stdout.buffer.write(response.SerializeToString())


if __name__ == "__main__":  # pragma: no cover - convenience execution entry.
    main()
