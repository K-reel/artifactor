"""Tests for forced adapter selection in ingestion."""

import tempfile
from pathlib import Path
import sys
from io import StringIO

from artifactor.ingest import Ingester
from artifactor.config import ArtifactorConfig
from artifactor.config.loader import load_config_from_dict


def test_forced_adapter_from_config():
    """Test that config.ingest.force_adapter forces adapter selection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "site"
        posts_dir = output_dir / "_posts"

        # Create config forcing socket adapter
        config_data = {
            "version": 1,
            "ingest": {"force_adapter": "socket"},
        }
        config = load_config_from_dict(config_data)

        # Create HTML fixture
        html_fixture = Path(tmpdir) / "test.html"
        html_fixture.write_text("""
            <html>
                <head>
                    <title>Test Article</title>
                    <meta property="og:title" content="Test Article">
                    <meta property="article:published_time" content="2024-01-15">
                </head>
                <body>
                    <article><h1>Test</h1><p>Content</p></article>
                </body>
            </html>
        """)

        # Create ingester with forced adapter
        ingester = Ingester(
            output_dir=output_dir,
            posts_dir=posts_dir,
            config=config,
            html_fixture=html_fixture,
        )

        # Ingest non-socket URL
        result = ingester.ingest_url("https://example.com/test")

        # Should succeed with forced socket adapter
        from artifactor.ingest import IngestStatus
        assert result.status in (IngestStatus.CREATED, IngestStatus.UPDATED)
        # Socket adapter should have been used for source
        assert result.filename is not None


def test_default_adapter_used_as_fallback_only():
    """Test that default_adapter is used ONLY as fallback, not forcing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "site"
        posts_dir = output_dir / "_posts"

        # Create config with socket as default_adapter (fallback)
        config_data = {
            "version": 1,
            "input": {"default_adapter": "socket"},
        }
        config = load_config_from_dict(config_data)

        # Create HTML fixture
        html_fixture = Path(tmpdir) / "test.html"
        html_fixture.write_text("""
            <html>
                <head>
                    <title>Socket Test</title>
                    <meta property="og:title" content="Socket Test">
                    <meta property="article:published_time" content="2024-01-15">
                </head>
                <body>
                    <article><h1>Test</h1><p>Content</p></article>
                </body>
            </html>
        """)

        # Create ingester
        ingester = Ingester(
            output_dir=output_dir,
            posts_dir=posts_dir,
            config=config,
            html_fixture=html_fixture,
        )

        # Ingest socket URL - should use socket adapter based on URL match, not fallback
        result = ingester.ingest_url("https://socket.dev/blog/test")

        # Should succeed - socket adapter selected by URL match
        from artifactor.ingest import IngestStatus
        assert result.status in (IngestStatus.CREATED, IngestStatus.UPDATED)


def test_explain_output_to_stderr(capsys):
    """Test that --explain output goes to stderr, not stdout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "site"
        posts_dir = output_dir / "_posts"

        # Create HTML fixture
        html_fixture = Path(tmpdir) / "test.html"
        html_fixture.write_text("""
            <html>
                <head>
                    <title>Test Article</title>
                    <meta property="og:title" content="Test Article">
                    <meta property="article:published_time" content="2024-01-15">
                </head>
                <body>
                    <article><h1>Test</h1><p>Content</p></article>
                </body>
            </html>
        """)

        # Create ingester with explain enabled
        ingester = Ingester(
            output_dir=output_dir,
            posts_dir=posts_dir,
            html_fixture=html_fixture,
            explain=True,
        )

        # Capture stderr
        old_stderr = sys.stderr
        sys.stderr = StringIO()

        try:
            # Ingest URL
            result = ingester.ingest_url("https://example.com/test")

            # Get stderr output
            stderr_output = sys.stderr.getvalue()

            # Explanation should be in stderr
            assert "adapter:" in stderr_output.lower()

        finally:
            sys.stderr = old_stderr


def test_forced_adapter_unknown_fails():
    """Test that unknown forced adapter causes ingestion to fail."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "site"
        posts_dir = output_dir / "_posts"

        # Create config with unknown forced adapter
        config_data = {
            "version": 1,
            "ingest": {"force_adapter": "unknown_adapter"},
        }
        config = load_config_from_dict(config_data)

        # Create HTML fixture
        html_fixture = Path(tmpdir) / "test.html"
        html_fixture.write_text("<html><body>Test</body></html>")

        # Create ingester
        ingester = Ingester(
            output_dir=output_dir,
            posts_dir=posts_dir,
            config=config,
            html_fixture=html_fixture,
        )

        # Try to ingest - should fail with ValueError
        result = ingester.ingest_url("https://example.com/test")

        # Should fail
        from artifactor.ingest import IngestStatus
        assert result.status == IngestStatus.FAILED
        assert "Unknown adapter" in result.error


def test_force_adapter_can_force_generic():
    """Test that force_adapter can force generic adapter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "site"
        posts_dir = output_dir / "_posts"

        # Create config forcing generic adapter
        config_data = {
            "version": 1,
            "ingest": {"force_adapter": "generic"},
        }
        config = load_config_from_dict(config_data)

        # Create HTML fixture
        html_fixture = Path(tmpdir) / "test.html"
        html_fixture.write_text("""
            <html>
                <head>
                    <title>Socket Test</title>
                    <meta property="og:title" content="Socket Test">
                    <meta property="article:published_time" content="2024-01-15">
                </head>
                <body>
                    <article><h1>Test</h1><p>Content</p></article>
                </body>
            </html>
        """)

        # Create ingester
        ingester = Ingester(
            output_dir=output_dir,
            posts_dir=posts_dir,
            config=config,
            html_fixture=html_fixture,
        )

        # Ingest socket URL - should force generic even though socket would match
        result = ingester.ingest_url("https://socket.dev/blog/test")

        # Should succeed with generic adapter forced
        from artifactor.ingest import IngestStatus
        assert result.status in (IngestStatus.CREATED, IngestStatus.UPDATED)


def test_cli_adapter_sets_force_adapter():
    """Test that CLI --adapter sets ingest.force_adapter."""
    config = ArtifactorConfig()
    merged = config.merge_cli_overrides(force_adapter="socket")

    # Should set ingest.force_adapter, not input.default_adapter
    assert merged.ingest.force_adapter == "socket"
    assert merged.input.default_adapter == "generic"  # Should remain unchanged


def test_unknown_adapter_error_message_sorted():
    """Test that unknown adapter error message has sorted adapter list."""
    from artifactor.sources.registry import AdapterRegistry

    registry = AdapterRegistry()

    try:
        registry.select_adapter("https://example.com", force_adapter="unknown")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        error_msg = str(e)
        assert "Unknown adapter 'unknown'" in error_msg
        assert "Available adapters: generic, socket" in error_msg  # Sorted alphabetically
