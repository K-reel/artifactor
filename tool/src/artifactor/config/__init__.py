"""Configuration system for Artifactor."""

from .loader import load_config, discover_config_file
from .schema import ArtifactorConfig

__all__ = ["ArtifactorConfig", "load_config", "discover_config_file"]
