"""Data models for Artifactor."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    """Canonical article schema for Artifactor.

    Represents a cleaned, structured article ready for Jekyll post generation.
    """

    title: str
    date: str  # YYYY-MM-DD format
    slug: str
    canonical_url: str
    source: str
    html: str  # Already-cleaned HTML body
    authors: Optional[list[str]] = field(default_factory=list)
    tags: Optional[list[str]] = field(default_factory=list)

    def __post_init__(self):
        """Validate and normalize data."""
        # Ensure date is in YYYY-MM-DD format
        if isinstance(self.date, datetime):
            self.date = self.date.strftime("%Y-%m-%d")

        # Ensure lists are not None
        if self.authors is None:
            self.authors = []
        if self.tags is None:
            self.tags = []

    @property
    def filename(self) -> str:
        """Generate Jekyll post filename: YYYY-MM-DD-slug.html"""
        return f"{self.date}-{self.slug}.html"
