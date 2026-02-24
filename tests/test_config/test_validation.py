"""Config validation: malformed YAML, missing fields, invalid types."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from konko_agent.config.loader import load_config
from konko_agent.config.models import AgentConfig, FieldConfig, PersonalityConfig


def test_load_valid_minimal_config(configs_dir: Path) -> None:
    """Valid minimal YAML loads and validates."""
    if not (configs_dir / "minimal_agent.yaml").exists():
        pytest.skip("configs/minimal_agent.yaml not found")
    config = load_config(configs_dir / "minimal_agent.yaml")
    assert config.name
    assert len(config.fields) >= 1
    assert config.personality.greeting


def test_load_malformed_yaml_raises() -> None:
    """Malformed YAML raises."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("foo: [\n  bar\n")  # invalid YAML
        path = f.name
    try:
        with pytest.raises((yaml.YAMLError, ValueError)):
            load_config(path)
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_empty_file_raises() -> None:
    """Empty YAML raises ValueError."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("")
        path = f.name
    try:
        with pytest.raises(ValueError, match="empty|Invalid"):
            load_config(path)
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_missing_required_fields_raises() -> None:
    """YAML missing required fields (e.g. fields, personality) raises."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump({"name": "OnlyName"}, f)
        path = f.name
    try:
        with pytest.raises(ValueError, match="Invalid config|validation"):
            load_config(path)
    finally:
        Path(path).unlink(missing_ok=True)


def test_load_invalid_field_type_raises() -> None:
    """Invalid field type raises validation error."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(
            {
                "name": "A",
                "fields": [{"name": "x", "type": "invalid_type", "prompt": "?"}],
                "personality": {"tone": "friendly", "greeting": "Hi", "closing": "Bye"},
            },
            f,
        )
        path = f.name
    try:
        with pytest.raises(ValueError, match="Invalid config|validation"):
            load_config(path)
    finally:
        Path(path).unlink(missing_ok=True)


def test_agent_config_static_models() -> None:
    """Static Pydantic models validate correctly."""
    config = AgentConfig(
        name="Test",
        fields=[
            FieldConfig(name="email", type="email", prompt="Email?"),
        ],
        personality=PersonalityConfig(
            greeting="Hi",
            closing="Bye",
            style="conversational",
            formality="casual",
            use_emojis=True,
            emoji_list=["👋"],
        ),
    )
    assert config.fields[0].type == "email"
    assert config.personality.greeting == "Hi"
    assert config.personality.style == "conversational"
    assert config.personality.use_emojis is True


def test_agent_config_personality_optional_fields_default() -> None:
    """Optional personality fields should default correctly when omitted."""
    config = AgentConfig(
        name="Test",
        fields=[
            FieldConfig(name="email", type="email", prompt="Email?"),
        ],
        personality=PersonalityConfig(greeting="Hi", closing="Bye"),
    )
    assert config.personality.style is None
    assert config.personality.formality is None
    assert config.personality.use_emojis is False
    assert config.personality.emoji_list == []
