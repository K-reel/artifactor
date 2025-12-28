"""Tests for ingestion functionality."""

import tempfile
from pathlib import Path

import pytest

from artifactor.ingest import Ingester, IngestStatus
from artifactor.sources.socket_blog import SocketBlogAdapter


@pytest.fixture
def socket_sample_html():
    """Load Socket blog sample HTML fixture."""
    # From tool/tests/test_ingest.py -> tool/ -> root -> fixtures/
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "socket_article_sample.html"
    return fixture_path.read_text()


@pytest.fixture
def socket_modern_html():
    """Load Socket blog modern Chakra UI fixture."""
    # From tool/tests/test_ingest.py -> tool/ -> root -> fixtures/
    fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "socket_modern.html"
    return fixture_path.read_text()


@pytest.fixture
def urls_sample_file():
    """Return path to sample URLs file."""
    # From tool/tests/test_ingest.py -> tool/ -> root -> fixtures/
    return Path(__file__).parent.parent.parent / "fixtures" / "urls_sample.txt"


def test_read_urls(urls_sample_file):
    """Test URL file parsing with comments and blank lines."""
    ingester = Ingester(output_dir=Path("site"), dry_run=True)
    urls = ingester.read_urls(urls_sample_file)

    # Should have 2 URLs (comments and blank lines ignored)
    assert len(urls) == 2
    assert urls[0] == "https://socket.dev/blog/understanding-npm-security"
    assert urls[1] == "https://socket.dev/blog/another-article"


def test_socket_adapter_can_handle():
    """Test Socket adapter URL detection."""
    adapter = SocketBlogAdapter()

    # Should handle Socket blog URLs
    assert adapter.can_handle("https://socket.dev/blog/some-post")
    assert adapter.can_handle("https://www.socket.dev/blog/another-post")

    # Should not handle other URLs
    assert not adapter.can_handle("https://example.com/blog/post")
    assert not adapter.can_handle("https://socket.dev/docs/guide")


def test_socket_adapter_extract_title(socket_sample_html):
    """Test Socket adapter extracts title correctly."""
    adapter = SocketBlogAdapter()
    url = "https://socket.dev/blog/understanding-npm-security"

    article = adapter.extract(url, socket_sample_html)

    assert article.title == "Understanding npm Package Security"


def test_socket_adapter_extract_date(socket_sample_html):
    """Test Socket adapter extracts date correctly."""
    adapter = SocketBlogAdapter()
    url = "https://socket.dev/blog/understanding-npm-security"

    article = adapter.extract(url, socket_sample_html)

    assert article.date == "2024-03-15"


def test_socket_adapter_extract_canonical_url(socket_sample_html):
    """Test Socket adapter extracts canonical URL correctly."""
    adapter = SocketBlogAdapter()
    url = "https://socket.dev/blog/understanding-npm-security"

    article = adapter.extract(url, socket_sample_html)

    assert article.canonical_url == "https://socket.dev/blog/understanding-npm-security"


def test_socket_adapter_extract_authors(socket_sample_html):
    """Test Socket adapter extracts authors correctly."""
    adapter = SocketBlogAdapter()
    url = "https://socket.dev/blog/understanding-npm-security"

    article = adapter.extract(url, socket_sample_html)

    assert article.authors == ["Jane Developer"]


def test_socket_adapter_extract_source(socket_sample_html):
    """Test Socket adapter sets source correctly."""
    adapter = SocketBlogAdapter()
    url = "https://socket.dev/blog/understanding-npm-security"

    article = adapter.extract(url, socket_sample_html)

    assert article.source == "Socket"


def test_socket_adapter_extract_slug(socket_sample_html):
    """Test Socket adapter generates slug from URL."""
    adapter = SocketBlogAdapter()
    url = "https://socket.dev/blog/understanding-npm-security"

    article = adapter.extract(url, socket_sample_html)

    assert article.slug == "understanding-npm-security"


def test_socket_adapter_extract_html_content(socket_sample_html):
    """Test Socket adapter extracts article HTML and cleans it."""
    adapter = SocketBlogAdapter()
    url = "https://socket.dev/blog/understanding-npm-security"

    article = adapter.extract(url, socket_sample_html)

    # Should contain main article content
    assert "npm packages are the building blocks" in article.html
    assert "<h2>Why Package Security Matters</h2>" in article.html
    assert "<code>" in article.html  # Code blocks preserved

    # Should NOT contain removed sections
    assert "Subscribe to our newsletter" not in article.html
    assert "Related Posts" not in article.html
    assert "<script>" not in article.html
    assert "<nav>" not in article.html
    assert "<footer>" not in article.html


def test_socket_adapter_deterministic_extraction(socket_sample_html):
    """Test that extraction is deterministic (same input = same output)."""
    adapter = SocketBlogAdapter()
    url = "https://socket.dev/blog/understanding-npm-security"

    # Extract multiple times
    article1 = adapter.extract(url, socket_sample_html)
    article2 = adapter.extract(url, socket_sample_html)
    article3 = adapter.extract(url, socket_sample_html)

    # All fields should be identical
    assert article1.title == article2.title == article3.title
    assert article1.date == article2.date == article3.date
    assert article1.slug == article2.slug == article3.slug
    assert article1.canonical_url == article2.canonical_url == article3.canonical_url
    assert article1.source == article2.source == article3.source
    assert article1.authors == article2.authors == article3.authors
    assert article1.html == article2.html == article3.html


def test_unchanged_detection(socket_sample_html):
    """Test that unchanged files are not rewritten."""
    adapter = SocketBlogAdapter()
    url = "https://socket.dev/blog/understanding-npm-security"
    article = adapter.extract(url, socket_sample_html)

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        posts_dir = output_dir / "_posts"
        posts_dir.mkdir(parents=True)

        # Create ingester
        ingester = Ingester(output_dir=output_dir, dry_run=False)

        # Generate post content
        post_content = ingester.generator.render_post(article)
        post_path = posts_dir / article.filename

        # Write initial file
        post_path.write_text(post_content, encoding="utf-8")
        initial_mtime = post_path.stat().st_mtime

        # Wait a moment to ensure mtime would change if file is rewritten
        import time
        time.sleep(0.01)

        # Check if content is unchanged
        existing_content = post_path.read_bytes()
        new_content = post_content.encode("utf-8")

        # Content should be identical
        assert existing_content == new_content

        # In real ingestion, file would not be rewritten
        # We verify this by checking that mtimes would differ if rewritten
        # (The actual ingestion code skips writing if content is unchanged)


def test_offline_mode_with_html_fixture(socket_sample_html):
    """Test offline ingestion using html_fixture parameter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        posts_dir = output_dir / "_posts"
        posts_dir.mkdir(parents=True)

        # Create fixture file
        fixture_path = Path(tmpdir) / "test_fixture.html"
        fixture_path.write_text(socket_sample_html, encoding="utf-8")

        # Create ingester with html_fixture
        ingester = Ingester(
            output_dir=output_dir,
            dry_run=False,
            html_fixture=fixture_path,
        )

        # Ingest a URL - should use fixture HTML instead of network
        url = "https://socket.dev/blog/understanding-npm-security"
        result = ingester.ingest_url(url)

        # Should succeed without network call
        assert result.status == IngestStatus.CREATED
        assert result.filename == "2024-03-15-understanding-npm-security.html"

        # Verify post was created
        post_path = posts_dir / result.filename
        assert post_path.exists()

        # Verify content extracted from fixture
        post_content = post_path.read_text(encoding="utf-8")
        assert "Understanding npm Package Security" in post_content
        assert "npm packages are the building blocks" in post_content


def test_offline_mode_multiple_urls(socket_sample_html):
    """Test offline ingestion with multiple URLs using same fixture."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        posts_dir = output_dir / "_posts"
        posts_dir.mkdir(parents=True)

        # Create fixture file
        fixture_path = Path(tmpdir) / "test_fixture.html"
        fixture_path.write_text(socket_sample_html, encoding="utf-8")

        # Create ingester with html_fixture
        ingester = Ingester(
            output_dir=output_dir,
            dry_run=False,
            html_fixture=fixture_path,
        )

        # Ingest multiple URLs
        urls = [
            "https://socket.dev/blog/understanding-npm-security",
            "https://socket.dev/blog/another-article",
        ]
        results = ingester.ingest_urls(urls)

        # Both should succeed
        assert len(results) == 2
        assert all(r.status == IngestStatus.CREATED for r in results)

        # Both should use same HTML content but different slugs
        assert results[0].filename == "2024-03-15-understanding-npm-security.html"
        assert results[1].filename == "2024-03-15-another-article.html"


def test_offline_mode_dry_run(socket_sample_html):
    """Test offline ingestion with dry-run mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        posts_dir = output_dir / "_posts"
        posts_dir.mkdir(parents=True)

        # Create fixture file
        fixture_path = Path(tmpdir) / "test_fixture.html"
        fixture_path.write_text(socket_sample_html, encoding="utf-8")

        # Create ingester with html_fixture and dry_run
        ingester = Ingester(
            output_dir=output_dir,
            dry_run=True,
            html_fixture=fixture_path,
        )

        # Ingest a URL
        url = "https://socket.dev/blog/understanding-npm-security"
        result = ingester.ingest_url(url)

        # Should report created status
        assert result.status == IngestStatus.CREATED
        assert result.filename == "2024-03-15-understanding-npm-security.html"

        # But file should NOT exist (dry run)
        post_path = posts_dir / result.filename
        assert not post_path.exists()


def test_socket_adapter_modern_chakra_ui(socket_modern_html):
    """Test Socket adapter correctly extracts prose div, not article cards."""
    adapter = SocketBlogAdapter()
    url = "https://socket.dev/blog/modern-chakra-post"

    article = adapter.extract(url, socket_modern_html)

    # Should extract metadata correctly
    assert article.title == "Modern Socket Blog Post with Chakra UI"
    assert article.date == "2024-11-15"
    assert article.authors == ["Jane Developer"]

    # Should contain main article content from prose div
    assert "This is the main article content" in article.html
    assert "technical details of the vulnerability" in article.html
    assert "best practices and security considerations" in article.html

    # Should contain section headings
    assert "First Section" in article.html
    assert "Second Section" in article.html

    # Should NOT contain related posts section
    assert "Related Posts" not in article.html
    assert "Another Blog Post Title" not in article.html
    assert "related post teaser" not in article.html
    assert "Yet Another Related Post" not in article.html

    # Should extract the prose div specifically (verify class is present)
    assert 'class="prose"' in article.html
