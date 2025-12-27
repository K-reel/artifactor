"""Base adapter interface for content extraction."""

from abc import ABC, abstractmethod
from artifactor.models import Article


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
