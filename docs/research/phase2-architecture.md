# Phase 2 Architecture Design Notes

## Layered Generator Architecture
- **Descriptor Analysis Layer**
  - Parses `CodeGeneratorRequest` descriptors into an internal model that hides protobuf API noise.
  - Normalizes package, dependency, and option metadata so downstream layers receive resolved symbol information.
  - Provides semantic validation hooks (e.g., unsupported field options, deprecated features) before code emission begins.
- **Type Mapping Layer**
  - Maps protobuf primitives, enums, messages, and oneofs into Unreal Engine types following UE naming conventions.
  - Hosts the `TypeResolver` service responsible for overridable mappings (e.g., custom numeric or container types).
  - Surfaces well-defined extension points for future proto3 semantics without leaking them to the rendering tier.
- **Template-driven Rendering Layer**
  - Accepts normalized models and produces header/source pairs through a rendering abstraction.
  - Coordinates helper generation (conversion utilities, registration code) while isolating text formatting concerns.
  - Manages dependency-aware file emission, ensuring deterministic ordering for testing and incremental rebuilds.

## Template Engine Strategy
- Favor a lightweight rendering abstraction named `ITemplateRenderer` with two initial implementations:
  - **`fmt`-based renderer** for minimal dependencies and tight control over format strings when templates are simple.
  - **`inja`-based renderer** to support more expressive templates (conditionals/loops) when we outgrow manual string assembly.
- The architecture routes all code generation through `ITemplateRenderer`, enabling per-project overrides without touching generator internals.
- Decision criteria:
  - Start with `fmt` for Phase 2 prototyping to validate models and reduce cognitive load.
  - Keep `inja` integration ready behind a factory/CLI switch for teams who prefer declarative templates.
  - Ensure renderers share a common template asset layout so swapping implementations does not invalidate test baselines.

## Configuration & CLI Design
- **TypeResolver Overrides**
  - Allow configuration files (YAML/TOML) to override primitive/container mappings and inject custom UE wrapper types.
  - CLI flags take precedence for quick experimentation, but persistable configs live alongside project repositories.
  - Support layered lookup: defaults → config file → CLI to make behavior predictable.
- **Namespace and Output Controls**
  - Provide explicit options for generated C++ namespace roots, module prefixes, and output directory partitioning (headers vs sources).
  - Expose switches for per-package namespace overrides and optional UE module registration blocks.
- **Option Precedence Model**
  - Establish a deterministic merge order: builtin defaults < project config < user config path (if distinct) < environment variables < CLI flags.
  - Document conflict resolution (e.g., last writer wins with warnings for incompatible combinations).
  - Surface diagnostics when required parameters are missing after precedence resolution.

## Extensibility Points
- **Generator Pipeline**
  - Structure pipeline stages (analysis → mapping → rendering → emission) as composable steps with clear data contracts.
  - Introduce middleware hooks so future proto3 support or feature toggles can insert processing stages without rewriting the core.
- **Feature Hooks**
  - Define interfaces for proto3-specific behaviors (e.g., `optional` semantics, `Any` helpers) that can be enabled as UE versions evolve.
  - Allow Unreal Engine release updates to extend metadata emission (Reflection macros, subsystem registration) via plugin-like modules.
  - Maintain compatibility shims so experimental features can be toggled per target without affecting stable pipelines.
