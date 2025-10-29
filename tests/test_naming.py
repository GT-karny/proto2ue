from pathlib import Path
import json

import pytest

from proto2ue.naming import NameResolver, load_naming_rules


def test_name_resolver_avoids_reserved_and_collisions(tmp_path: Path) -> None:
    config_path = tmp_path / "naming.json"
    config_path.write_text(
        json.dumps(
            {
                "reserved_symbols": ["FVector"],
                "collision_suffix": "Proto",
                "overrides": {},
            }
        )
    )

    rules = load_naming_rules(str(config_path))
    resolver = NameResolver(rules)

    name_a = resolver.register("math.Vector", "F", "Vector")
    assert name_a == "FProtoVector"

    name_b = resolver.register("math.Vector2", "F", "Vector2")
    assert name_b == "FVector2"

    # Re-registering should be idempotent
    assert resolver.register("math.Vector", "F", "Vector") == name_a


def test_name_resolver_respects_overrides(tmp_path: Path) -> None:
    config_path = tmp_path / "naming.json"
    config_path.write_text(
        json.dumps(
            {
                "reserved_symbols": ["FDemoType"],
                "collision_suffix": "Proto",
                "overrides": {"demo.Type": "FDemoType"},
            }
        )
    )

    rules = load_naming_rules(str(config_path))
    resolver = NameResolver(rules)

    with pytest.raises(ValueError):
        resolver.register("demo.Type", "F", "Type")
