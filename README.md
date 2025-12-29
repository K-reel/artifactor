<p align="center">
  <img src="assets/artifactor-logo.jpg" alt="Artifactor logo" width="220" />
</p>

# Artifactor

**Artifactor** is a Python-based CLI tool that generates Jekyll HTML posts from structured article data. I treat my writing like an artifact pipeline.

**Live demo:** https://k-reel.github.io/artifactor/

![CI](https://github.com/K-reel/artifactor/actions/workflows/ci.yml/badge.svg)
![Pages](https://github.com/K-reel/artifactor/actions/workflows/pages.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

## What is Artifactor?

Artifactor transforms article data into static site posts with deterministic, reproducible output. It can:
- **Ingest from URLs**: Fetch and extract content from web articles (Phase 1)
- **Generate from fixtures**: Create posts from structured JSON (Phase 0)
- **Output Jekyll posts**: HTML files with YAML front matter, ready for GitHub Pages

Think of it as a build pipeline for content: stable inputs produce stable outputs, every time.

## Features

**Phase 1 (Current)**: URL ingestion with content extraction
- Fetch articles from curated URL lists
- Extract title, date, authors, and canonical HTML
- Support for Socket blog and generic web pages
- Deterministic output: same input → same bytes

**Phase 0**: Scaffolding and foundation
- Generate posts from JSON fixtures
- Jekyll site structure with layouts
- Comprehensive test suite

## Installation

```bash
pip install artifactor
```

For development:

```bash
git clone https://github.com/K-reel/artifactor.git
cd artifactor
pip install -e ".[dev]"
```

## Versioning

- **v0.2.0**: Configuration system, adapter debugging tools, repo-root packaging, trusted publishing
- **v0.1.1**: CI workflow (offline-only, runs on every push/PR)
- **v0.1.0**: Initial release (scaffold + ingest + offline fixture mode)

## Repository Structure

```
artifactor/
├── tool/                          # Python package
│   ├── src/artifactor/           # Source code
│   │   ├── cli.py                # Typer-based CLI (scaffold, ingest)
│   │   ├── models.py             # Article dataclass
│   │   ├── generator.py          # Post generation logic
│   │   ├── fetch.py              # HTTP fetching
│   │   ├── ingest.py             # URL ingestion orchestration
│   │   ├── sources/              # Content extraction adapters
│   │   │   ├── base.py           # Adapter interface
│   │   │   ├── socket_blog.py    # Socket blog adapter
│   │   │   └── generic.py        # Generic fallback adapter
│   │   └── templates/            # Jinja2 templates
│   ├── tests/                    # Test suite
│   └── pyproject.toml            # Package configuration
├── site/                          # Jekyll site
│   ├── _config.yml               # Jekyll configuration
│   ├── _layouts/                 # Layout templates
│   ├── _posts/                   # Generated posts go here
│   ├── index.html                # Post listing
│   └── Gemfile                   # Ruby dependencies
├── fixtures/                      # Sample input data
│   ├── sample_article.json       # Example article (Phase 0)
│   ├── socket_article_sample.html # Socket blog HTML (testing)
│   └── urls_sample.txt           # Sample URL list
└── README.md                      # This file
```

## Quick Start

### For Users

```bash
# Install from PyPI
pip install artifactor

# Validate your configuration (creates default config if needed)
artifactor config validate

# Ingest URLs from a file
artifactor ingest --urls urls.txt

# List available adapters
artifactor adapters list
```

### For Developers

Get started with the development environment in four simple commands:

### 1. Install Dependencies

```bash
make install
```

This installs the Python package and development dependencies in editable mode.

### 2. Generate a Sample Post

```bash
make scaffold
```

This generates a Jekyll post from the sample fixture at `site/_posts/2024-03-15-writing-as-artifact-pipeline.html`.

### 3. Run Tests

```bash
make test
```

Runs the test suite to verify everything works correctly.

### 4. Serve the Site (Optional)

```bash
# First time only: install Ruby dependencies
cd site && bundle install && cd ..

# Start Jekyll server
make serve
```

Open [http://localhost:4000](http://localhost:4000) to view your generated posts.

**Prerequisites for Jekyll:**
- Ruby 2.7+ and Bundler installed
- On macOS: `brew install ruby && gem install bundler`

**Note on Gemfile.lock:**
We commit `site/Gemfile.lock` (Bundler dependency lockfile) to improve reproducibility. If your Ruby/Bundler environment differs:
1. Try `bundle install` first
2. If needed, run `bundle update --bundler`
3. Use `bundle update` only as a last resort

## Usage

### Make Targets

The easiest way to work with Artifactor is through the Makefile:

```bash
make help      # Show all available targets
make install   # Install Python package and dependencies
make scaffold  # Generate sample post from fixture
make ingest    # Ingest URLs (offline demo, no network)
make test      # Run test suite
make serve     # Start Jekyll development server
make clean     # Remove generated site files and caches
```

**Note on `make ingest`:** This target runs in offline demo mode using a sample HTML fixture. No network requests are made, making it safe for testing and CI environments. To ingest real URLs from the web, use the `artifactor ingest` command directly (see Phase 1 usage below).

### Phase 1: Ingest from URLs

**Create a URL list** (`urls.txt`):
```text
# URLs to ingest (one per line, # for comments)
https://socket.dev/blog/understanding-npm-security
https://socket.dev/blog/another-article

# Blank lines are ignored
```

**Ingest URLs** (with dry-run first):
```bash
# Dry run to preview
python3 -m artifactor ingest --urls urls.txt --out site/ --limit 2 --dry-run

# Actually generate posts
python3 -m artifactor ingest --urls urls.txt --out site/
```

**Options:**
- `--urls PATH`: File containing URLs (one per line, required)
- `--out PATH`: Output directory (default: `site/`)
- `--limit N`: Process only first N URLs (useful for testing)
- `--dry-run`: Show what would be done without writing
- `--timeout SECONDS`: Request timeout (default: 20)
- `--user-agent STRING`: Custom User-Agent header
- `--html-fixture PATH`: Use HTML file for offline testing (no network fetch)

**Offline testing:**
Use `--html-fixture` to test ingestion without network access:
```bash
python3 -m artifactor ingest --urls fixtures/urls_sample.txt --out site/ --html-fixture fixtures/socket_article_sample.html --dry-run
```
This processes URLs using the provided HTML file instead of fetching from the network. Useful for CI, demos, and development. In fixture mode, the URL is still used for adapter selection and filename slugging; multiple URLs may generate different filenames from the same fixture content.

**Status indicators:**
- `✓ CREATED`: New post created
- `↻ UPDATED`: Existing post updated
- `= UNCHANGED`: Content identical, not rewritten
- `✗ FAILED`: Extraction or fetch failed

### Phase 0: Generate from Fixtures

Generate posts from structured JSON:

```bash
artifactor scaffold --out site/ --fixture fixtures/sample_article.json
```

**Note:** If `artifactor` is not in your PATH, use:
```bash
python3 -m artifactor scaffold --out site/ --fixture fixtures/sample_article.json
```

### Article Schema

The canonical `Article` model has these fields:

```python
@dataclass
class Article:
    title: str              # Article title
    date: str               # Publication date (YYYY-MM-DD)
    slug: str               # URL-friendly identifier
    canonical_url: str      # Original article URL
    source: str             # Source publication name
    html: str               # Pre-cleaned HTML content
    authors: list[str]      # Optional list of authors
    tags: list[str]         # Optional list of tags
```

**Example fixture JSON:**

```json
{
  "title": "Example Article",
  "date": "2024-03-15",
  "slug": "example-article",
  "canonical_url": "https://example.com/article",
  "source": "Example Blog",
  "authors": ["Author Name"],
  "tags": ["tag1", "tag2"],
  "html": "<p>Article content here.</p>"
}
```

## Development

### Running Tests

```bash
make test
```

Or run pytest directly with coverage:

```bash
cd tool && python3 -m pytest --cov=artifactor --cov-report=term-missing
```

### Deterministic Output

Artifactor ensures **byte-for-byte identical output** for identical inputs:
- Stable YAML key ordering in front matter
- Normalized line endings (`\n`)
- No timestamps except the article date
- Consistent 2-space indentation for YAML lists

Run the determinism test specifically:

```bash
cd tool && python3 -m pytest tests/test_generator.py::test_generate_post_deterministic_file -v
```

### Adding New Fixtures

Create a JSON file in `fixtures/` following the Article schema, then generate a post:

```bash
artifactor scaffold --out site/ --fixture fixtures/your_article.json
# Or use make:
# Edit the Makefile scaffold target to point to your fixture
```

## Jekyll Site Details

### Layouts

**`_layouts/reprint.html`**: Renders article posts with:
- Title and date
- Author attribution (if provided)
- Reprint notice with canonical URL and source
- Tags (if provided)
- Full HTML content

### Configuration

**`_config.yml`**: Minimal Jekyll configuration with:
- Site title and description
- Markdown processor (kramdown)
- Permalink structure
- Build exclusions

### Local Development

```bash
cd site
bundle exec jekyll serve --livereload
```

The `--livereload` flag auto-refreshes your browser when files change.

## Design Principles

1. **Minimal and Deterministic**: Stable file paths, stable formatting, no unnecessary complexity
2. **HTML Posts**: Uses HTML with YAML front matter, not Markdown (we control the HTML)
3. **Local-First**: Easy to develop and build locally
4. **Testable**: Automated tests ensure deterministic output
5. **Extensible**: Clear separation between tool (Python) and site (Jekyll)

## Roadmap

**Phase 0 (Current)**: Repository scaffolding, sample post generation, local Jekyll build

**Future Phases**:
- Content ingestion from web sources
- Automated HTML cleaning and normalization
- Batch processing
- CI/CD integration
- Archive management

## Contributing

Contributions welcome! This is an open-source project focused on treating content like artifacts in a build pipeline.

## License

MIT License - see LICENSE file for details

## Requirements

- Python 3.10+
- Ruby 2.7+ (for Jekyll)
- Bundler

## Troubleshooting

**Command not found: `artifactor`**

Make sure you installed the package in editable mode:

```bash
cd tool
pip install -e .
```

**Jekyll fails to build**

Ensure you installed the Ruby dependencies:

```bash
cd site
bundle install
```

**Tests fail**

Make sure you're in the `tool` directory and have installed dev dependencies:

```bash
cd tool
pip install -e ".[dev]"
pytest
```

---

**Philosophy**: I treat my writing like an artifact pipeline—structured, versioned, and reproducible.
