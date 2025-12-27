"""Tests for post generation functionality."""

import json
from pathlib import Path
import tempfile

import pytest

from artifactor.models import Article
from artifactor.generator import PostGenerator


@pytest.fixture
def sample_article():
    """Create a sample Article for testing."""
    return Article(
        title="Test Article",
        date="2024-01-15",
        slug="test-article",
        canonical_url="https://example.com/test",
        source="Example Source",
        authors=["Test Author"],
        tags=["test", "example"],
        html="<p>This is a test article.</p>",
    )


@pytest.fixture
def sample_article_minimal():
    """Create a minimal Article without optional fields."""
    return Article(
        title="Minimal Article",
        date="2024-01-16",
        slug="minimal-article",
        canonical_url="https://example.com/minimal",
        source="Example Source",
        html="<p>Minimal content.</p>",
    )


def test_article_filename(sample_article):
    """Test that Article generates correct filename."""
    assert sample_article.filename == "2024-01-15-test-article.html"


def test_generate_front_matter(sample_article):
    """Test front matter generation with all fields."""
    generator = PostGenerator()
    front_matter = generator._generate_front_matter(sample_article)

    # Should be valid YAML
    assert "layout: reprint" in front_matter
    assert "title: Test Article" in front_matter
    assert "date: '2024-01-15'" in front_matter or "date: 2024-01-15" in front_matter
    assert "canonical_url: https://example.com/test" in front_matter
    assert "source: Example Source" in front_matter
    assert "authors:" in front_matter
    assert "- Test Author" in front_matter
    assert "tags:" in front_matter
    assert "- test" in front_matter
    assert "- example" in front_matter


def test_generate_front_matter_minimal(sample_article_minimal):
    """Test front matter generation without optional fields."""
    generator = PostGenerator()
    front_matter = generator._generate_front_matter(sample_article_minimal)

    # Should include required fields
    assert "layout: reprint" in front_matter
    assert "title: Minimal Article" in front_matter

    # Should not include empty optional fields
    assert "authors:" not in front_matter
    assert "tags:" not in front_matter


def test_render_post_deterministic(sample_article):
    """Test that rendering produces deterministic output."""
    generator = PostGenerator()

    # Render the same article multiple times
    output1 = generator.render_post(sample_article)
    output2 = generator.render_post(sample_article)
    output3 = generator.render_post(sample_article)

    # All outputs should be identical
    assert output1 == output2 == output3


def test_render_post_structure(sample_article):
    """Test that rendered post has correct structure."""
    generator = PostGenerator()
    output = generator.render_post(sample_article)

    # Should have YAML front matter delimiters
    assert output.startswith("---\n")
    assert "\n---\n" in output

    # Should contain the HTML content
    assert "<p>This is a test article.</p>" in output


def test_generate_post_creates_file(sample_article):
    """Test that generate_post creates a file with correct content."""
    generator = PostGenerator()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "_posts"
        output_path = generator.generate_post(sample_article, output_dir)

        # File should exist
        assert output_path.exists()
        assert output_path.name == "2024-01-15-test-article.html"

        # Content should match rendered output
        content = output_path.read_text(encoding="utf-8")
        expected = generator.render_post(sample_article)
        assert content == expected


def test_generate_post_deterministic_file(sample_article):
    """Test that generating the same post multiple times produces identical files."""
    generator = PostGenerator()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "_posts"

        # Generate the same post three times
        path1 = generator.generate_post(sample_article, output_dir)
        content1 = path1.read_bytes()

        path2 = generator.generate_post(sample_article, output_dir)
        content2 = path2.read_bytes()

        path3 = generator.generate_post(sample_article, output_dir)
        content3 = path3.read_bytes()

        # All files should be identical at the byte level
        assert content1 == content2 == content3


def test_load_article_from_fixture():
    """Test loading an Article from a JSON fixture."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        fixture_data = {
            "title": "Fixture Test",
            "date": "2024-02-20",
            "slug": "fixture-test",
            "canonical_url": "https://example.com/fixture",
            "source": "Test Source",
            "authors": ["Fixture Author"],
            "tags": ["fixture"],
            "html": "<p>Fixture content.</p>",
        }
        json.dump(fixture_data, f)
        fixture_path = Path(f.name)

    try:
        article = PostGenerator.load_article_from_fixture(fixture_path)

        assert article.title == "Fixture Test"
        assert article.date == "2024-02-20"
        assert article.slug == "fixture-test"
        assert article.canonical_url == "https://example.com/fixture"
        assert article.source == "Test Source"
        assert article.authors == ["Fixture Author"]
        assert article.tags == ["fixture"]
        assert article.html == "<p>Fixture content.</p>"
    finally:
        fixture_path.unlink()


def test_front_matter_stable_key_order(sample_article):
    """Test that front matter keys are in stable order."""
    generator = PostGenerator()
    front_matter = generator._generate_front_matter(sample_article)

    lines = front_matter.split("\n")
    keys = [line.split(":")[0] for line in lines if ":" in line and not line.startswith(" ")]

    # Keys should be in the expected order
    expected_order = ["layout", "title", "date", "canonical_url", "source", "authors", "tags"]
    assert keys == expected_order
