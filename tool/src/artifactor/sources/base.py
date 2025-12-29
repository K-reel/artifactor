"""Base adapter interface for content extraction."""

from abc import ABC, abstractmethod
from typing import Optional, List
from artifactor.models import Article


class AdapterMetadata:
    """Metadata describing an adapter's capabilities."""

    def __init__(
        self,
        name: str,
        description: str,
        priority: int = 50,
        match_patterns: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.priority = priority
        self.match_patterns = match_patterns or []


class SourceAdapter(ABC):
    """Base adapter for extracting article content from HTML."""

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Check if this adapter can handle the given URL.

        Args:
            url: URL to check

        Returns:
            True if this adapter can handle the URL
        """
        pass

    @abstractmethod
    def extract(self, url: str, html: str) -> Article:
        """Extract article content from HTML.

        Args:
            url: Source URL
            html: HTML content

        Returns:
            Article object with extracted content

        Raises:
            ValueError: If extraction fails or required data is missing
        """
        pass

    def get_metadata(self) -> AdapterMetadata:
        """Return metadata describing this adapter's capabilities.

        Subclasses should override this to provide accurate metadata.
        """
        return AdapterMetadata(
            name=self.__class__.__name__,
            description="No description provided",
            priority=50,
            match_patterns=[],
        )
