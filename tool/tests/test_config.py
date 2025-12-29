"""Tests for configuration system."""

import tempfile
from pathlib import Path

import pytest
import yaml

from artifactor.config import ArtifactorConfig, load_config, discover_config_file
from artifactor.config.loader import load_config_from_dict, config_to_dict
from artifactor.config.schema import ProjectConfig, InputConfig, DateConfig


def test_default_config():
    """Test that default config loads without errors."""
    config = ArtifactorConfig()

    # Check defaults
    assert config.version == 1
    assert config.project.timezone == "UTC"
    assert config.input.default_adapter == "generic"
    assert config.input.allow_network is True
    assert config.output.site_dir == "site"
    assert config.output.posts_dir == "site/_posts"
    assert config.ingest.date.require is False
    assert config.ingest.date.fallback_date is None


def test_config_discovery_no_file():
    """Test config discovery when no file exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        discovered = discover_config_file(Path(tmpdir))
        assert discovered is None


def test_config_discovery_yml():
    """Test config discovery finds artifactor.yml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir).resolve()

        # Create config file
        config_file = tmpdir_path / "artifactor.yml"
        config_file.write_text("version: 1\n")

        # Discover should find it (resolve both for comparison)
        discovered = discover_config_file(tmpdir_path)
        assert discovered.resolve() == config_file.resolve()


def test_config_discovery_yaml():
    """Test config discovery finds artifactor.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir).resolve()

        # Create config file
        config_file = tmpdir_path / "artifactor.yaml"
        config_file.write_text("version: 1\n")

        # Discover should find it (resolve both for comparison)
        discovered = discover_config_file(tmpdir_path)
        assert discovered.resolve() == config_file.resolve()


def test_config_discovery_prefers_yml():
    """Test that .yml is preferred over .yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir).resolve()

        # Create both files
        yml_file = tmpdir_path / "artifactor.yml"
        yaml_file = tmpdir_path / "artifactor.yaml"
        yml_file.write_text("version: 1\n")
        yaml_file.write_text("version: 1\n")

        # Discover should find .yml first (resolve both for comparison)
        discovered = discover_config_file(tmpdir_path)
        assert discovered.resolve() == yml_file.resolve()


def test_config_discovery_searches_up():
    """Test config discovery searches parent directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir).resolve()

        # Create nested directory structure
        subdir = tmpdir_path / "project" / "src" / "app"
        subdir.mkdir(parents=True)

        # Put config in parent
        config_file = tmpdir_path / "project" / "artifactor.yml"
        config_file.write_text("version: 1\n")

        # Discover from deep subdirectory should find it
        discovered = discover_config_file(subdir)
        assert discovered.resolve() == config_file.resolve()


def test_load_config_no_file():
    """Test loading config when no file exists (uses defaults)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set cwd to temp dir with no config
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            config = load_config()

            # Should use defaults
            assert config.version == 1
            assert config.output.site_dir == "site"
        finally:
            os.chdir(original_cwd)


def test_load_config_from_dict_minimal():
    """Test loading config from minimal dict."""
    data = {"version": 1}
    config = load_config_from_dict(data)

    assert config.version == 1
    assert config.output.site_dir == "site"  # Default


def test_load_config_from_dict_override_defaults():
    """Test loading config overrides defaults."""
    data = {
        "version": 1,
        "output": {"site_dir": "custom_site", "posts_dir": "custom_posts"},
        "input": {"allow_network": False},
    }
    config = load_config_from_dict(data)

    assert config.output.site_dir == "custom_site"
    assert config.output.posts_dir == "custom_posts"
    assert config.input.allow_network is False


def test_load_config_from_file():
    """Test loading config from YAML file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "artifactor.yml"
        config_file.write_text(
            """
version: 1
output:
  site_dir: test_site
  posts_dir: test_posts
"""
        )

        config = load_config(config_file)
        assert config.output.site_dir == "test_site"
        assert config.output.posts_dir == "test_posts"


def test_load_config_invalid_yaml():
    """Test loading config with invalid YAML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "artifactor.yml"
        config_file.write_text("invalid: [yaml")

        with pytest.raises(ValueError, match="Invalid YAML"):
            load_config(config_file)


def test_load_config_explicit_path_not_found():
    """Test loading config with explicit path that doesn't exist."""
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.yml"))


def test_config_validation_invalid_version():
    """Test config validation rejects invalid version."""
    with pytest.raises(ValueError, match="Unsupported config version"):
        ArtifactorConfig(version=99)


def test_config_validation_invalid_timezone():
    """Test config validation rejects invalid timezone."""
    with pytest.raises(ValueError, match="Invalid timezone"):
        ArtifactorConfig(project=ProjectConfig(timezone="Invalid"))


def test_config_validation_invalid_line_ending():
    """Test config validation rejects invalid line ending."""
    data = {
        "version": 1,
        "output": {"html": {"normalize_line_endings": "invalid"}},
    }
    with pytest.raises(ValueError, match="Invalid line ending"):
        load_config_from_dict(data)


def test_config_validation_invalid_dedupe_strategy():
    """Test config validation rejects invalid dedupe strategy."""
    data = {"version": 1, "ingest": {"dedupe": {"strategy": "invalid"}}}
    with pytest.raises(ValueError, match="Invalid dedupe strategy"):
        load_config_from_dict(data)


def test_config_validation_invalid_slug_strategy():
    """Test config validation rejects invalid slug strategy."""
    data = {"version": 1, "ingest": {"slug": {"strategy": "invalid"}}}
    with pytest.raises(ValueError, match="Invalid slug strategy"):
        load_config_from_dict(data)


def test_config_validation_invalid_fallback_date():
    """Test config validation rejects invalid fallback date format."""
    data = {"version": 1, "ingest": {"date": {"fallback_date": "invalid-date"}}}
    with pytest.raises(ValueError, match="Invalid fallback_date format"):
        load_config_from_dict(data)


def test_config_validation_valid_fallback_date():
    """Test config validation accepts valid fallback date."""
    data = {"version": 1, "ingest": {"date": {"fallback_date": "2024-01-15"}}}
    config = load_config_from_dict(data)
    assert config.ingest.date.fallback_date == "2024-01-15"


def test_config_validation_null_fallback_date():
    """Test config validation accepts null fallback date."""
    data = {"version": 1, "ingest": {"date": {"fallback_date": None}}}
    config = load_config_from_dict(data)
    assert config.ingest.date.fallback_date is None


def test_config_merge_cli_overrides_site_dir():
    """Test CLI overrides for site_dir."""
    config = ArtifactorConfig()
    merged = config.merge_cli_overrides(site_dir=Path("/custom/site"))

    assert merged.output.site_dir == "/custom/site"
    # Original unchanged
    assert config.output.site_dir == "site"


def test_config_merge_cli_overrides_posts_dir():
    """Test CLI overrides for posts_dir."""
    config = ArtifactorConfig()
    merged = config.merge_cli_overrides(posts_dir=Path("/custom/posts"))

    assert merged.output.posts_dir == "/custom/posts"


def test_config_merge_cli_overrides_offline():
    """Test CLI override for offline mode."""
    config = ArtifactorConfig()
    merged = config.merge_cli_overrides(offline=True)

    assert merged.input.allow_network is False
    # Original unchanged
    assert config.input.allow_network is True


def test_config_merge_cli_overrides_allow_network():
    """Test CLI override for allow_network."""
    config = ArtifactorConfig()

    # Disable network
    merged = config.merge_cli_overrides(allow_network=False)
    assert merged.input.allow_network is False

    # Enable network
    merged = config.merge_cli_overrides(allow_network=True)
    assert merged.input.allow_network is True


def test_config_merge_cli_overrides_offline_precedence():
    """Test that offline flag takes precedence over allow_network."""
    config = ArtifactorConfig()

    # offline=True should override allow_network=True
    merged = config.merge_cli_overrides(offline=True, allow_network=True)
    assert merged.input.allow_network is False


def test_config_merge_cli_overrides_require_date():
    """Test CLI override for require_date."""
    config = ArtifactorConfig()
    merged = config.merge_cli_overrides(require_date=True)

    assert merged.ingest.date.require is True


def test_config_merge_cli_overrides_fallback_date():
    """Test CLI override for fallback_date."""
    config = ArtifactorConfig()
    merged = config.merge_cli_overrides(fallback_date="2024-03-15")

    assert merged.ingest.date.fallback_date == "2024-03-15"


def test_config_merge_cli_overrides_force_adapter():
    """Test CLI override for force_adapter."""
    config = ArtifactorConfig()
    merged = config.merge_cli_overrides(force_adapter="socket")

    assert merged.ingest.force_adapter == "socket"


def test_config_merge_precedence():
    """Test merge precedence: CLI > config file > defaults."""
    # Start with defaults
    config = ArtifactorConfig()
    assert config.output.site_dir == "site"

    # Load from dict (simulating config file)
    data = {"version": 1, "output": {"site_dir": "file_site"}}
    config = load_config_from_dict(data)
    assert config.output.site_dir == "file_site"

    # CLI override takes precedence
    merged = config.merge_cli_overrides(site_dir=Path("cli_site"))
    assert merged.output.site_dir == "cli_site"


def test_config_to_dict():
    """Test converting config to dict."""
    config = ArtifactorConfig()
    config_dict = config_to_dict(config)

    assert config_dict["version"] == 1
    assert config_dict["output"]["site_dir"] == "site"
    assert config_dict["input"]["allow_network"] is True


def test_config_to_dict_roundtrip():
    """Test config -> dict -> config roundtrip."""
    config1 = ArtifactorConfig()
    config_dict = config_to_dict(config1)
    config2 = load_config_from_dict(config_dict)

    # Should be equivalent
    assert config1.version == config2.version
    assert config1.output.site_dir == config2.output.site_dir
    assert config1.input.allow_network == config2.input.allow_network


def test_config_empty_file():
    """Test loading empty config file uses defaults."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "artifactor.yml"
        config_file.write_text("")

        config = load_config(config_file)
        assert config.version == 1
        assert config.output.site_dir == "site"


def test_config_deterministic_fallback_date_null():
    """Test that fallback_date defaults to null (not today)."""
    config = ArtifactorConfig()
    assert config.ingest.date.fallback_date is None

    # Should not default to today's date
    from datetime import date

    today = date.today().strftime("%Y-%m-%d")
    assert config.ingest.date.fallback_date != today

