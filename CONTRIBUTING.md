# Contributing to Artifactor

Thank you for your interest in contributing to Artifactor! This guide will help you get started.

## Quick Start

### Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   make install
   ```
3. Run tests to verify setup:
   ```bash
   make test
   ```

### Development Workflow

```bash
# Run all tests
make test

# Test offline ingestion (no network)
make ingest

# Generate a sample post
make scaffold
```

## Project Principles

### 1. Deterministic Output
- Same input → same bytes every time
- No timestamps except article dates
- Stable YAML key ordering
- Normalized line endings

### 2. Offline-First Testing
- All tests use fixtures, never network calls
- CI runs in complete offline mode
- Use `--html-fixture` for ingestion tests

### 3. Fixture Strategy
- Fixtures live in `fixtures/` directory
- Use synthetic content (no copyrighted material)
- Include representative HTML structures
- Keep fixtures minimal but realistic

## Adding a Source Adapter

Adapters extract content from specific websites. Here's how to add one:

### 1. Create the adapter file

Create `tool/src/artifactor/sources/your_source.py`:

```python
from .base import SourceAdapter
from artifactor.models import Article
from bs4 import BeautifulSoup

class YourSourceAdapter(SourceAdapter):
    def can_handle(self, url: str) -> bool:
        """Check if this adapter handles the URL."""
        return "yoursource.com" in url

    def extract(self, url: str, html: str) -> Article:
        """Extract article from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # Extract metadata and content
        title = self._extract_title(soup)
        date = self._extract_date(soup)
        # ... more extraction logic

        return Article(
            title=title,
            date=date,
            slug=self._generate_slug(url, title),
            canonical_url=url,
            source="Your Source",
            html=self._extract_article_html(soup),
            authors=self._extract_authors(soup),
            tags=[],
        )
```

### 2. Create a test fixture

Add `fixtures/yoursource_sample.html` with representative HTML:
- Include meta tags (og:title, article:published_time, etc.)
- Add main article content
- Include sections to be removed (nav, footer, newsletter)

### 3. Register the adapter

In `tool/src/artifactor/ingest.py`, add your adapter to the list:

```python
self.adapters = [
    SocketBlogAdapter(),
    YourSourceAdapter(),  # Add here
    GenericAdapter(),     # Keep as fallback
]
```

### 4. Write tests

Add tests in `tool/tests/test_ingest.py`:

```python
def test_yoursource_adapter_extract(yoursource_sample_html):
    adapter = YourSourceAdapter()
    url = "https://yoursource.com/article"

    article = adapter.extract(url, yoursource_sample_html)

    assert article.title == "Expected Title"
    assert article.date == "2024-01-01"
    assert "main content" in article.html
    assert "unwanted section" not in article.html
```

## Code Style

- Follow existing patterns in the codebase
- Use type hints for function signatures
- Keep functions focused and testable
- Add docstrings for public APIs

## Testing Requirements

All contributions must:
- ✅ Pass existing test suite (`make test`)
- ✅ Add tests for new functionality
- ✅ Maintain offline-first approach (no network in tests)
- ✅ Preserve deterministic output

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run tests (`make test`)
5. Commit with clear messages
6. Push to your fork
7. Open a pull request

### PR Guidelines

- **Title**: Clear, concise description
- **Description**:
  - What changed and why
  - Testing approach
  - Any breaking changes
- **Checklist**:
  - [ ] Tests pass locally
  - [ ] New tests added for new features
  - [ ] Documentation updated (if needed)
  - [ ] No network calls in tests

## Questions?

- Open an issue for discussion
- Check existing issues and PRs
- Read the README for architecture overview

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
