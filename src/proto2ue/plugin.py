"""Protocol Buffers compiler plugin entry point for proto2ue."""
from __future__ import annotations

import sys
from typing import Any

from google.protobuf.compiler import plugin_pb2

from .descriptor_loader import DescriptorLoader


def analyze_descriptors(request: plugin_pb2.CodeGeneratorRequest) -> Any:
    """Normalize descriptors into the proto2ue intermediate model."""

    loader = DescriptorLoader(request)
    return loader.load()


def main() -> None:
    """Execute the protoc plugin workflow."""

    request_payload = sys.stdin.buffer.read()

    request = plugin_pb2.CodeGeneratorRequest()
    if request_payload:
        request.ParseFromString(request_payload)

    # Obtain intermediate representation for downstream pipeline stages.
    intermediate_representation = analyze_descriptors(request)
    del intermediate_representation

    response = plugin_pb2.CodeGeneratorResponse()
    sys.stdout.buffer.write(response.SerializeToString())


if __name__ == "__main__":  # pragma: no cover - convenience execution entry.
    main()
