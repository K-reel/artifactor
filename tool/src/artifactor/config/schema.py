"""Configuration schema for Artifactor."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List


@dataclass
class ProjectConfig:
    """Project-level configuration."""

    timezone: str = "UTC"


@dataclass
class InputConfig:
    """Input/fetch configuration."""

    default_adapter: str = "generic"
    allow_network: bool = True
    user_agent: str = "Artifactor/0.1 (+https://github.com/K-reel/artifactor)"


@dataclass
class FilenameConfig:
    """Filename pattern configuration."""

    pattern: str = "{date:%Y-%m-%d}-{slug}.html"
    undated_prefix: str = "undated"


@dataclass
class FrontMatterConfig:
    """Front matter configuration."""

    stable_key_order: List[str] = field(
        default_factory=lambda: [
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
        ]
    )
    defaults: dict = field(
        default_factory=lambda: {
            "layout": "post",
            "author": None,
            "tags": [],
            "categories": [],
        }
    )


@dataclass
class HtmlConfig:
    """HTML normalization configuration."""

    normalize_line_endings: str = "lf"
    strip_trailing_whitespace: bool = True
    ensure_single_trailing_newline: bool = True


@dataclass
class OutputConfig:
    """Output configuration."""

    site_dir: str = "site"
    posts_dir: str = "site/_posts"
    overwrite: bool = False
    filename: FilenameConfig = field(default_factory=FilenameConfig)
    front_matter: FrontMatterConfig = field(default_factory=FrontMatterConfig)
    html: HtmlConfig = field(default_factory=HtmlConfig)


@dataclass
class DedupeConfig:
    """Deduplication configuration."""

    strategy: str = "canonical_url"


@dataclass
class DateConfig:
    """Date handling configuration."""

    require: bool = False
    fallback_date: Optional[str] = None


@dataclass
class SlugConfig:
    """Slug generation configuration."""

    max_len: int = 80
    strategy: str = "title_then_path"


@dataclass
class IngestConfig:
    """Ingestion configuration."""

    canonicalize_urls: bool = True
    dedupe: DedupeConfig = field(default_factory=DedupeConfig)
    date: DateConfig = field(default_factory=DateConfig)
    slug: SlugConfig = field(default_factory=SlugConfig)
    force_adapter: Optional[str] = None


@dataclass
class ArtifactorConfig:
    """Complete Artifactor configuration.

    This configuration follows deterministic principles:
    - No time-based defaults (fallback_date must be explicit)
    - Stable ordering for all sequences
    - LF line endings enforced
    """

    version: int = 1
    project: ProjectConfig = field(default_factory=ProjectConfig)
    input: InputConfig = field(default_factory=InputConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    ingest: IngestConfig = field(default_factory=IngestConfig)

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self):
        """Validate configuration values."""
        # Version check
        if self.version != 1:
            raise ValueError(f"Unsupported config version: {self.version}. Expected: 1")

        # Timezone validation
        valid_timezones = ["UTC"]  # Extensible
        if self.project.timezone not in valid_timezones:
            raise ValueError(
                f"Invalid timezone: {self.project.timezone}. Currently only UTC is supported."
            )

        # Line ending validation
        valid_line_endings = ["lf", "crlf"]
        if self.output.html.normalize_line_endings not in valid_line_endings:
            raise ValueError(
                f"Invalid line ending: {self.output.html.normalize_line_endings}. "
                f"Must be one of: {', '.join(valid_line_endings)}"
            )

        # Dedupe strategy validation
        valid_dedupe_strategies = ["canonical_url", "content_hash"]
        if self.ingest.dedupe.strategy not in valid_dedupe_strategies:
            raise ValueError(
                f"Invalid dedupe strategy: {self.ingest.dedupe.strategy}. "
                f"Must be one of: {', '.join(valid_dedupe_strategies)}"
            )

        # Slug strategy validation
        valid_slug_strategies = ["title_then_path", "path_then_title", "title_only"]
        if self.ingest.slug.strategy not in valid_slug_strategies:
            raise ValueError(
                f"Invalid slug strategy: {self.ingest.slug.strategy}. "
                f"Must be one of: {', '.join(valid_slug_strategies)}"
            )

        # Date fallback validation
        if self.ingest.date.fallback_date is not None:
            try:
                from datetime import datetime

                datetime.strptime(self.ingest.date.fallback_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError(
                    f"Invalid fallback_date format: {self.ingest.date.fallback_date}. "
                    "Must be YYYY-MM-DD or null."
                )

    def merge_cli_overrides(
        self,
        config_file: Optional[Path] = None,
        site_dir: Optional[Path] = None,
        posts_dir: Optional[Path] = None,
        allow_network: Optional[bool] = None,
        offline: Optional[bool] = None,
        require_date: Optional[bool] = None,
        fallback_date: Optional[str] = None,
        force_adapter: Optional[str] = None,
    ) -> "ArtifactorConfig":
        """Merge CLI overrides into config (returns new instance).

        Precedence: CLI args > config file > defaults

        Args:
            config_file: Not used for merging, just for tracking
            site_dir: Override site_dir
            posts_dir: Override posts_dir
            allow_network: Override allow_network
            offline: If True, sets allow_network=False
            require_date: Override require_date
            fallback_date: Override fallback_date
            force_adapter: Override force_adapter

        Returns:
            New ArtifactorConfig instance with overrides applied
        """
        # Create a copy by reconstructing
        new_config = ArtifactorConfig(
            version=self.version,
            project=ProjectConfig(timezone=self.project.timezone),
            input=InputConfig(
                default_adapter=self.input.default_adapter,
                allow_network=self.input.allow_network,
                user_agent=self.input.user_agent,
            ),
            output=OutputConfig(
                site_dir=str(site_dir) if site_dir else self.output.site_dir,
                posts_dir=str(posts_dir) if posts_dir else self.output.posts_dir,
                overwrite=self.output.overwrite,
                filename=FilenameConfig(
                    pattern=self.output.filename.pattern,
                    undated_prefix=self.output.filename.undated_prefix,
                ),
                front_matter=FrontMatterConfig(
                    stable_key_order=self.output.front_matter.stable_key_order.copy(),
                    defaults=self.output.front_matter.defaults.copy(),
                ),
                html=HtmlConfig(
                    normalize_line_endings=self.output.html.normalize_line_endings,
                    strip_trailing_whitespace=self.output.html.strip_trailing_whitespace,
                    ensure_single_trailing_newline=self.output.html.ensure_single_trailing_newline,
                ),
            ),
            ingest=IngestConfig(
                canonicalize_urls=self.ingest.canonicalize_urls,
                dedupe=DedupeConfig(strategy=self.ingest.dedupe.strategy),
                date=DateConfig(
                    require=require_date if require_date is not None else self.ingest.date.require,
                    fallback_date=fallback_date if fallback_date is not None else self.ingest.date.fallback_date,
                ),
                slug=SlugConfig(
                    max_len=self.ingest.slug.max_len,
                    strategy=self.ingest.slug.strategy,
                ),
                force_adapter=force_adapter if force_adapter is not None else self.ingest.force_adapter,
            ),
        )

        # Handle offline flag (overrides allow_network)
        if offline:
            new_config.input.allow_network = False
        elif allow_network is not None:
            new_config.input.allow_network = allow_network

        return new_config
