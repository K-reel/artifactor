"""Adapter registry for deterministic adapter selection."""

from typing import List, Tuple, Optional
from .base import SourceAdapter
from .socket_blog import SocketBlogAdapter
from .generic import GenericAdapter


class AdapterRegistry:
    """Central registry for source adapters with deterministic selection."""

    def __init__(self):
        self._adapters: List[SourceAdapter] = []
        self._register_builtin_adapters()

    def _register_builtin_adapters(self):
        """Register built-in adapters in priority order."""
        self.register(SocketBlogAdapter())
        self.register(GenericAdapter())

    def register(self, adapter: SourceAdapter):
        """Register an adapter.

        Args:
            adapter: SourceAdapter instance to register
        """
        self._adapters.append(adapter)

    def get_all_adapters(self) -> List[SourceAdapter]:
        """Get all registered adapters in priority order (high to low).

        Returns:
            List of adapters sorted by priority (descending), then name (ascending) for deterministic tie-breaking
        """
        return sorted(
            self._adapters,
            key=lambda a: (-a.get_metadata().priority, a.get_metadata().name),
        )

    def get_adapter_by_name(self, name: str) -> Optional[SourceAdapter]:
        """Get an adapter by its name.

        Args:
            name: Adapter name to find

        Returns:
            SourceAdapter instance or None if not found
        """
        for adapter in self._adapters:
            if adapter.get_metadata().name == name:
                return adapter
        return None

    def select_adapter(
        self, url: str, force_adapter: Optional[str] = None, fallback_adapter: str = "generic"
    ) -> Tuple[SourceAdapter, str]:
        """Select the best adapter for a URL.

        Args:
            url: URL to match
            force_adapter: If provided, force use of this adapter by name
            fallback_adapter: Adapter to use when no adapter matches (default: generic)

        Returns:
            Tuple of (selected adapter, explanation string)

        Raises:
            ValueError: If forced adapter is unknown or no adapter can handle the URL
        """
        # Handle forced adapter selection
        if force_adapter:
            adapter = self.get_adapter_by_name(force_adapter)
            if adapter is None:
                available = sorted([a.get_metadata().name for a in self._adapters])
                raise ValueError(
                    f"Unknown adapter '{force_adapter}'. "
                    f"Available adapters: {', '.join(available)}"
                )
            metadata = adapter.get_metadata()
            explanation = (
                f"Forced adapter: {metadata.name} (priority={metadata.priority})"
            )
            return adapter, explanation

        # Get adapters in priority order
        adapters = self.get_all_adapters()

        for adapter in adapters:
            if adapter.can_handle(url):
                metadata = adapter.get_metadata()
                explanation = (
                    f"Selected adapter: {metadata.name} (priority={metadata.priority})"
                )
                return adapter, explanation

        # No adapter matched - use fallback
        adapter = self.get_adapter_by_name(fallback_adapter)
        if adapter is None:
            available = sorted([a.get_metadata().name for a in self._adapters])
            raise ValueError(
                f"Fallback adapter '{fallback_adapter}' not found. "
                f"Available adapters: {', '.join(available)}"
            )
        metadata = adapter.get_metadata()
        explanation = (
            f"Fallback adapter: {metadata.name} (no adapter matched URL)"
        )
        return adapter, explanation

    def debug_selection(
        self, url: str, html: Optional[str] = None
    ) -> List[dict]:
        """Debug adapter selection for a URL.

        Args:
            url: URL to debug
            html: Optional HTML content for extraction testing

        Returns:
            List of dicts with adapter name, can_handle result, priority, patterns, and match_score
        """
        adapters = self.get_all_adapters()
        results = []

        for adapter in adapters:
            metadata = adapter.get_metadata()
            can_handle = adapter.can_handle(url)
            match_score = 1 if can_handle else 0

            result = {
                "name": metadata.name,
                "can_handle": can_handle,
                "priority": metadata.priority,
                "description": metadata.description,
                "match_patterns": metadata.match_patterns,
                "match_score": match_score,
            }

            # If HTML provided, attempt extraction to test adapter
            if html and can_handle:
                try:
                    article = adapter.extract(url, html)
                    result["extraction_success"] = True
                    result["extracted_title"] = article.title[:50] if article.title else None
                except Exception as e:
                    result["extraction_success"] = False
                    result["extraction_error"] = str(e)[:100]

            results.append(result)

        return results


# Global registry instance
_registry: Optional[AdapterRegistry] = None


def get_registry() -> AdapterRegistry:
    """Get the global adapter registry instance.

    Returns:
        AdapterRegistry singleton
    """
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
    return _registry
