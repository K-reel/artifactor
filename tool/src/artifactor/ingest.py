"""Ingestion orchestration for Artifactor."""

import hashlib
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING
from enum import Enum

import typer

from .fetch import fetch_url, FetchResult
from .generator import PostGenerator
from .models import Article
from .sources.registry import get_registry

if TYPE_CHECKING:
    from .config import ArtifactorConfig


class IngestStatus(Enum):
    """Status of ingesting a URL."""

    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    FAILED = "failed"


class IngestResult:
    """Result of ingesting a single URL."""

    def __init__(
        self,
        url: str,
        status: IngestStatus,
        filename: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.url = url
        self.status = status
        self.filename = filename
        self.error = error


class Ingester:
    """Orchestrates the ingestion of URLs into Jekyll posts."""

    def __init__(
        self,
        output_dir: Path,
        posts_dir: Optional[Path] = None,
        timeout: int = 20,
        user_agent: str = "Artifactor/0.1 (+https://github.com/K-reel/artifactor)",
        dry_run: bool = False,
        html_fixture: Optional[Path] = None,
        config: Optional["ArtifactorConfig"] = None,
        explain: bool = False,
    ):
        self.output_dir = output_dir
        self.posts_dir = posts_dir if posts_dir else (output_dir / "_posts")
        self.timeout = timeout
        self.user_agent = user_agent
        self.dry_run = dry_run
        self.html_fixture = html_fixture
        self.config = config
        self.explain = explain
        self.generator = PostGenerator()
        self.registry = get_registry()

    def read_urls(self, urls_file: Path) -> List[str]:
        """Read and parse URLs from file.

        Args:
            urls_file: Path to file containing URLs (one per line)

        Returns:
            List of URLs

        Format:
            - One URL per line
            - Blank lines ignored
            - Lines starting with # are comments
        """
        urls = []
        with open(urls_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip blank lines and comments
                if not line or line.startswith("#"):
                    continue
                urls.append(line)
        return urls

    def ingest_url(self, url: str) -> IngestResult:
        """Ingest a single URL.

        Args:
            url: URL to ingest

        Returns:
            IngestResult with status and details
        """
        try:
            # Get HTML content (from network or fixture)
            if self.html_fixture:
                # Offline mode: use fixture HTML
                html = self.html_fixture.read_text(encoding="utf-8")
                final_url = url  # Use original URL for adapter selection
            else:
                # Online mode: fetch from network
                result = fetch_url(url, timeout=self.timeout, user_agent=self.user_agent)

                if not result.success:
                    return IngestResult(
                        url=url,
                        status=IngestStatus.FAILED,
                        error=f"HTTP {result.status_code}",
                    )

                html = result.html
                final_url = result.final_url

            # Select adapter (with forced adapter from config if specified)
            forced_adapter = self.config.ingest.force_adapter if self.config else None
            fallback_adapter = self.config.input.default_adapter if self.config else "generic"

            adapter, explanation = self._select_adapter(final_url, forced_adapter, fallback_adapter)

            # Print explanation to stderr if requested
            if self.explain:
                typer.echo(f"  {explanation}", err=True)

            # Extract article
            article = adapter.extract(final_url, html)

            # Generate post
            output_path = self.posts_dir / article.filename

            # Check if file already exists (before writing)
            file_exists = output_path.exists()

            # Check if file exists and is unchanged
            if file_exists and not self.dry_run:
                existing_content = output_path.read_bytes()
                new_content = self.generator.render_post(article).encode("utf-8")

                if existing_content == new_content:
                    return IngestResult(
                        url=url,
                        status=IngestStatus.UNCHANGED,
                        filename=article.filename,
                    )

            # Write post (unless dry run)
            if not self.dry_run:
                self.generator.generate_post(article, self.posts_dir)
                status = IngestStatus.UPDATED if file_exists else IngestStatus.CREATED
            else:
                # In dry run, determine status without writing
                status = IngestStatus.UPDATED if file_exists else IngestStatus.CREATED

            return IngestResult(
                url=url,
                status=status,
                filename=article.filename,
            )

        except Exception as e:
            return IngestResult(
                url=url,
                status=IngestStatus.FAILED,
                error=str(e),
            )

    def ingest_urls(self, urls: List[str], limit: Optional[int] = None) -> List[IngestResult]:
        """Ingest multiple URLs.

        Args:
            urls: List of URLs to ingest
            limit: Optional limit on number of URLs to process

        Returns:
            List of IngestResult objects
        """
        if limit:
            urls = urls[:limit]

        results = []
        for url in urls:
            result = self.ingest_url(url)
            results.append(result)

        return results

    def _select_adapter(
        self, url: str, forced_adapter: Optional[str] = None, fallback_adapter: str = "generic"
    ):
        """Select the appropriate adapter for a URL.

        Args:
            url: URL to select adapter for
            forced_adapter: Optional adapter name to force selection
            fallback_adapter: Adapter to use when no adapter matches (default: generic)

        Returns:
            Tuple of (adapter, explanation)
        """
        return self.registry.select_adapter(
            url, force_adapter=forced_adapter, fallback_adapter=fallback_adapter
        )
