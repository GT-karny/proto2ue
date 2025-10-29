from __future__ import annotations

import pytest

from proto2ue.config import DEFAULT_RESERVED_IDENTIFIERS, GeneratorConfig


def test_generator_config_defaults_include_reserved_identifiers() -> None:
    config = GeneratorConfig.from_parameter_string(None)
    assert config.reserved_identifiers == DEFAULT_RESERVED_IDENTIFIERS
    assert config.include_package_in_names is True


def test_generator_config_allows_overriding_reserved_identifiers(tmp_path) -> None:
    reserved_file = tmp_path / "reserved.txt"
    reserved_file.write_text("FExtraType\n# comment\nFAnotherType\n", encoding="utf-8")

    parameter = (
        "reserved_identifiers=FCustomOne|FCustomTwo,"
        "extra_reserved_identifiers=FThird,"
        f"reserved_identifiers_file={reserved_file}"
    )

    config = GeneratorConfig.from_parameter_string(parameter)

    assert config.reserved_identifiers == (
        "FCustomOne",
        "FCustomTwo",
        "FThird",
        "FExtraType",
        "FAnotherType",
    )


def test_generator_config_parses_rename_overrides(tmp_path) -> None:
    rename_file = tmp_path / "renames.txt"
    rename_file.write_text(
        "physics.Vector:FPhysicsVector\nphysics.Color:EPhysicsColor\n",
        encoding="utf-8",
    )

    parameter = (
        "rename_overrides=demo.Widget:FDemoWidget|demo.Token:FDemoToken,"
        f"rename_overrides_file={rename_file}"
    )

    config = GeneratorConfig.from_parameter_string(parameter)

    assert config.rename_overrides == {
        "demo.Widget": "FDemoWidget",
        "demo.Token": "FDemoToken",
        "physics.Vector": "FPhysicsVector",
        "physics.Color": "EPhysicsColor",
    }


def test_generator_config_allows_disabling_package_names() -> None:
    config = GeneratorConfig.from_parameter_string("include_package_in_names=false")

    assert config.include_package_in_names is False


def test_generator_config_rename_overrides_require_separator() -> None:
    with pytest.raises(ValueError):
        GeneratorConfig.from_parameter_string("rename_overrides=invalid-entry")
