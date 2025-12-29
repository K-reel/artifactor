"""Configuration file discovery and loading."""

import sys
from pathlib import Path
from typing import Optional, Dict, Any

import yaml

from .schema import (
    ArtifactorConfig,
    ProjectConfig,
    InputConfig,
    OutputConfig,
    IngestConfig,
    FilenameConfig,
    FrontMatterConfig,
    HtmlConfig,
    DedupeConfig,
    DateConfig,
    SlugConfig,
)


def discover_config_file(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Discover config file by searching up from start_dir.

    Search order:
    1. artifactor.yml
    2. artifactor.yaml

    Search locations (in order):
    1. start_dir (default: cwd)
    2. Parent directories up to filesystem root

    Args:
        start_dir: Starting directory (default: current working directory)

    Returns:
        Path to config file if found, None otherwise
    """
    if start_dir is None:
        start_dir = Path.cwd()

    start_dir = start_dir.resolve()

    # Try each directory from start_dir up to root
    current = start_dir
    while True:
        # Check for config files in priority order
        for filename in ["artifactor.yml", "artifactor.yaml"]:
            config_path = current / filename
            if config_path.is_file():
                return config_path

        # Move up one directory
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            break
        current = parent

    return None


def load_config_from_dict(data: Dict[str, Any]) -> ArtifactorConfig:
    """Load config from a dictionary (from YAML parsing).

    Args:
        data: Dictionary with config data

    Returns:
        ArtifactorConfig instance

    Raises:
        ValueError: If config is invalid
    """
    # Extract version
    version = data.get("version", 1)

    # Build project config
    project_data = data.get("project", {})
    project = ProjectConfig(
        timezone=project_data.get("timezone", "UTC"),
    )

    # Build input config
    input_data = data.get("input", {})
    input_config = InputConfig(
        default_adapter=input_data.get("default_adapter", "generic"),
        allow_network=input_data.get("allow_network", True),
        user_agent=input_data.get(
            "user_agent", "Artifactor/0.1 (+https://github.com/K-reel/artifactor)"
        ),
    )

    # Build output config
    output_data = data.get("output", {})

    # Filename config
    filename_data = output_data.get("filename", {})
    filename = FilenameConfig(
        pattern=filename_data.get("pattern", "{date:%Y-%m-%d}-{slug}.html"),
        undated_prefix=filename_data.get("undated_prefix", "undated"),
    )

    # Front matter config
    front_matter_data = output_data.get("front_matter", {})
    front_matter = FrontMatterConfig(
        stable_key_order=front_matter_data.get(
            "stable_key_order",
            [
                "layout",
                "title",
                "date",
                "author",
                "source_url",
                "canonical_url",
                "tags",
                "categories",
                "excerpt",
                "lastmod",
            ],
        ),
        defaults=front_matter_data.get(
            "defaults",
            {
                "layout": "post",
                "author": None,
                "tags": [],
                "categories": [],
            },
        ),
    )

    # HTML config
    html_data = output_data.get("html", {})
    html = HtmlConfig(
        normalize_line_endings=html_data.get("normalize_line_endings", "lf"),
        strip_trailing_whitespace=html_data.get("strip_trailing_whitespace", True),
        ensure_single_trailing_newline=html_data.get("ensure_single_trailing_newline", True),
    )

    output = OutputConfig(
        site_dir=output_data.get("site_dir", "site"),
        posts_dir=output_data.get("posts_dir", "site/_posts"),
        overwrite=output_data.get("overwrite", False),
        filename=filename,
        front_matter=front_matter,
        html=html,
    )

    # Build ingest config
    ingest_data = data.get("ingest", {})

    # Dedupe config
    dedupe_data = ingest_data.get("dedupe", {})
    dedupe = DedupeConfig(
        strategy=dedupe_data.get("strategy", "canonical_url"),
    )

    # Date config
    date_data = ingest_data.get("date", {})
    date_config = DateConfig(
        require=date_data.get("require", False),
        fallback_date=date_data.get("fallback_date", None),
    )

    # Slug config
    slug_data = ingest_data.get("slug", {})
    slug = SlugConfig(
        max_len=slug_data.get("max_len", 80),
        strategy=slug_data.get("strategy", "title_then_path"),
    )

    ingest = IngestConfig(
        canonicalize_urls=ingest_data.get("canonicalize_urls", True),
        dedupe=dedupe,
        date=date_config,
        slug=slug,
        force_adapter=ingest_data.get("force_adapter", None),
    )

    # Construct final config (validation happens in __post_init__)
    return ArtifactorConfig(
        version=version,
        project=project,
        input=input_config,
        output=output,
        ingest=ingest,
    )


def load_config(config_path: Optional[Path] = None) -> ArtifactorConfig:
    """Load configuration from file or use defaults.

    Args:
        config_path: Explicit path to config file, or None to discover

    Returns:
        ArtifactorConfig instance

    Raises:
        ValueError: If config file is invalid
        FileNotFoundError: If explicit config_path doesn't exist
    """
    if config_path is None:
        # Try to discover config file
        config_path = discover_config_file()

    if config_path is None:
        # No config file found, use defaults
        return ArtifactorConfig()

    # Explicit path must exist
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    # Load and parse YAML
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            # Empty file - use defaults
            return ArtifactorConfig()

        if not isinstance(data, dict):
            raise ValueError(f"Config file must contain a YAML mapping, got: {type(data)}")

        return load_config_from_dict(data)

    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {e}")


def config_to_dict(config: ArtifactorConfig) -> Dict[str, Any]:
    """Convert config to dictionary (for printing/export).

    Args:
        config: ArtifactorConfig instance

    Returns:
        Dictionary representation with stable key ordering
    """
    return {
        "version": config.version,
        "project": {
            "timezone": config.project.timezone,
        },
        "input": {
            "default_adapter": config.input.default_adapter,
            "allow_network": config.input.allow_network,
            "user_agent": config.input.user_agent,
        },
        "output": {
            "site_dir": config.output.site_dir,
            "posts_dir": config.output.posts_dir,
            "overwrite": config.output.overwrite,
            "filename": {
                "pattern": config.output.filename.pattern,
                "undated_prefix": config.output.filename.undated_prefix,
            },
            "front_matter": {
                "stable_key_order": config.output.front_matter.stable_key_order,
                "defaults": config.output.front_matter.defaults,
            },
            "html": {
                "normalize_line_endings": config.output.html.normalize_line_endings,
                "strip_trailing_whitespace": config.output.html.strip_trailing_whitespace,
                "ensure_single_trailing_newline": config.output.html.ensure_single_trailing_newline,
            },
        },
        "ingest": {
            "canonicalize_urls": config.ingest.canonicalize_urls,
            "dedupe": {
                "strategy": config.ingest.dedupe.strategy,
            },
            "date": {
                "require": config.ingest.date.require,
                "fallback_date": config.ingest.date.fallback_date,
            },
            "slug": {
                "max_len": config.ingest.slug.max_len,
                "strategy": config.ingest.slug.strategy,
            },
            "force_adapter": config.ingest.force_adapter,
        },
    }
