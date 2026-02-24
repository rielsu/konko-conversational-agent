"""Load and validate agent config from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from konko_agent.config.models import AgentConfig


def load_config(path: str | Path) -> AgentConfig:
    """
    Load YAML file and validate into AgentConfig.
    Raises FileNotFoundError, yaml.YAMLError, or ValidationError on invalid config.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if data is None:
        raise ValueError("Config file is empty")

    try:
        return AgentConfig.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"Invalid config: {e}") from e
