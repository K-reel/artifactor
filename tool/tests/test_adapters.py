"""Tests for adapter registry and selection."""

from artifactor.sources.registry import AdapterRegistry, get_registry
from artifactor.sources.socket_blog import SocketBlogAdapter
from artifactor.sources.generic import GenericAdapter


def test_registry_initialization():
    """Test that registry initializes with built-in adapters."""
    registry = AdapterRegistry()
    adapters = registry.get_all_adapters()

    # Should have 2 built-in adapters
    assert len(adapters) == 2

    # Should be sorted by priority (high to low)
    priorities = [a.get_metadata().priority for a in adapters]
    assert priorities == sorted(priorities, reverse=True)


def test_registry_adapter_order():
    """Test that adapters are returned in deterministic priority order."""
    registry = AdapterRegistry()
    adapters = registry.get_all_adapters()

    # Socket adapter (priority 80) should come before generic (priority 10)
    assert adapters[0].get_metadata().name == "socket"
    assert adapters[1].get_metadata().name == "generic"


def test_select_adapter_socket_url():
    """Test adapter selection for Socket.dev URL."""
    registry = AdapterRegistry()
    adapter, explanation = registry.select_adapter("https://socket.dev/blog/test")

    # Should select socket adapter
    assert adapter.get_metadata().name == "socket"
    assert "socket" in explanation
    assert "priority=80" in explanation


def test_select_adapter_generic_url():
    """Test adapter selection for generic URL."""
    registry = AdapterRegistry()
    adapter, explanation = registry.select_adapter("https://example.com/article")

    # Should select generic adapter
    assert adapter.get_metadata().name == "generic"
    assert "generic" in explanation
    assert "priority=10" in explanation


def test_debug_selection_socket_url():
    """Test debug output for Socket.dev URL."""
    registry = AdapterRegistry()
    debug_info = registry.debug_selection("https://socket.dev/blog/test")

    # Should return info for all adapters
    assert len(debug_info) == 2

    # First should be socket (higher priority)
    assert debug_info[0]["name"] == "socket"
    assert debug_info[0]["can_handle"] is True
    assert debug_info[0]["priority"] == 80

    # Second should be generic
    assert debug_info[1]["name"] == "generic"
    assert debug_info[1]["can_handle"] is True
    assert debug_info[1]["priority"] == 10


def test_debug_selection_generic_url():
    """Test debug output for generic URL."""
    registry = AdapterRegistry()
    debug_info = registry.debug_selection("https://example.com/article")

    # Should return info for all adapters
    assert len(debug_info) == 2

    # Socket should not match
    socket_info = [d for d in debug_info if d["name"] == "socket"][0]
    assert socket_info["can_handle"] is False

    # Generic should match
    generic_info = [d for d in debug_info if d["name"] == "generic"][0]
    assert generic_info["can_handle"] is True


def test_adapter_metadata_socket():
    """Test Socket adapter metadata."""
    adapter = SocketBlogAdapter()
    metadata = adapter.get_metadata()

    assert metadata.name == "socket"
    assert metadata.priority == 80
    assert "Socket.dev" in metadata.description
    assert "socket.dev/blog/*" in metadata.match_patterns


def test_adapter_metadata_generic():
    """Test generic adapter metadata."""
    adapter = GenericAdapter()
    metadata = adapter.get_metadata()

    assert metadata.name == "generic"
    assert metadata.priority == 10
    assert "fallback" in metadata.description.lower()
    assert "*" in metadata.match_patterns


def test_global_registry_singleton():
    """Test that get_registry returns same instance."""
    registry1 = get_registry()
    registry2 = get_registry()

    # Should be same instance
    assert registry1 is registry2


def test_adapter_selection_deterministic():
    """Test that adapter selection is deterministic."""
    registry = AdapterRegistry()

    # Select same URL multiple times
    results = []
    for _ in range(5):
        adapter, explanation = registry.select_adapter("https://socket.dev/blog/test")
        results.append((adapter.get_metadata().name, explanation))

    # All results should be identical
    assert all(r == results[0] for r in results)


def test_debug_selection_deterministic_order():
    """Test that debug selection returns adapters in consistent order."""
    registry = AdapterRegistry()

    # Debug same URL multiple times
    results = []
    for _ in range(5):
        debug_info = registry.debug_selection("https://example.com/test")
        names = [d["name"] for d in debug_info]
        results.append(names)

    # All results should have same order
    assert all(r == results[0] for r in results)
    # Order should be: socket, generic (by priority)
    assert results[0] == ["socket", "generic"]


def test_forced_adapter_selection_socket():
    """Test forcing socket adapter selection."""
    registry = AdapterRegistry()

    # Force socket adapter even for non-socket URL
    adapter, explanation = registry.select_adapter(
        "https://example.com/test", force_adapter="socket"
    )

    assert adapter.get_metadata().name == "socket"
    assert "Forced adapter: socket" in explanation


def test_forced_adapter_selection_generic():
    """Test forcing generic adapter selection."""
    registry = AdapterRegistry()

    # Force generic adapter for socket URL
    adapter, explanation = registry.select_adapter(
        "https://socket.dev/blog/test", force_adapter="generic"
    )

    assert adapter.get_metadata().name == "generic"
    assert "Forced adapter: generic" in explanation


def test_forced_adapter_unknown_raises_error():
    """Test that forcing unknown adapter raises ValueError."""
    registry = AdapterRegistry()

    try:
        registry.select_adapter("https://example.com", force_adapter="unknown")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unknown adapter 'unknown'" in str(e)
        assert "Available adapters:" in str(e)
        assert "socket" in str(e)
        assert "generic" in str(e)


def test_tie_break_by_name():
    """Test that adapters with same priority are sorted by name."""
    from artifactor.sources.base import SourceAdapter, AdapterMetadata
    from artifactor.models import Article

    class ZebraAdapter(SourceAdapter):
        def can_handle(self, url: str) -> bool:
            return "zebra" in url

        def extract(self, url: str, html: str) -> Article:
            pass

        def get_metadata(self):
            return AdapterMetadata(name="zebra", description="Test", priority=50)

    class AppleAdapter(SourceAdapter):
        def can_handle(self, url: str) -> bool:
            return "apple" in url

        def extract(self, url: str, html: str) -> Article:
            pass

        def get_metadata(self):
            return AdapterMetadata(name="apple", description="Test", priority=50)

    registry = AdapterRegistry()
    # Clear default adapters
    registry._adapters = []
    # Register in reverse alphabetical order
    registry.register(ZebraAdapter())
    registry.register(AppleAdapter())

    adapters = registry.get_all_adapters()
    names = [a.get_metadata().name for a in adapters]

    # Should be sorted alphabetically when priority is same
    assert names == ["apple", "zebra"]


def test_debug_selection_includes_match_score():
    """Test that debug selection includes match_score."""
    registry = AdapterRegistry()
    debug_info = registry.debug_selection("https://socket.dev/blog/test")

    # All entries should have match_score
    for info in debug_info:
        assert "match_score" in info
        assert info["match_score"] in (0, 1)

    # Socket should match (score 1)
    socket_info = [d for d in debug_info if d["name"] == "socket"][0]
    assert socket_info["match_score"] == 1

    # Generic should also match (score 1)
    generic_info = [d for d in debug_info if d["name"] == "generic"][0]
    assert generic_info["match_score"] == 1


def test_debug_selection_with_html_extraction():
    """Test debug selection with HTML fixture for extraction testing."""
    registry = AdapterRegistry()

    # Simple HTML for testing
    html = """
    <html>
        <head>
            <title>Test Article</title>
            <meta property="og:title" content="Test Article">
            <meta property="article:published_time" content="2024-01-15">
        </head>
        <body>
            <article>
                <h1>Test Article</h1>
                <p>Content here</p>
            </article>
        </body>
    </html>
    """

    debug_info = registry.debug_selection("https://example.com/test", html=html)

    # Generic adapter should have extraction results
    generic_info = [d for d in debug_info if d["name"] == "generic"][0]
    assert "extraction_success" in generic_info
    # May succeed or fail depending on date extraction, but should have the field

    # Socket adapter should not attempt extraction (can't handle this URL)
    socket_info = [d for d in debug_info if d["name"] == "socket"][0]
    assert "extraction_success" not in socket_info


def test_get_adapter_by_name():
    """Test getting adapter by name."""
    registry = AdapterRegistry()

    # Get existing adapters
    socket_adapter = registry.get_adapter_by_name("socket")
    assert socket_adapter is not None
    assert socket_adapter.get_metadata().name == "socket"

    generic_adapter = registry.get_adapter_by_name("generic")
    assert generic_adapter is not None
    assert generic_adapter.get_metadata().name == "generic"

    # Get non-existent adapter
    unknown_adapter = registry.get_adapter_by_name("unknown")
    assert unknown_adapter is None
