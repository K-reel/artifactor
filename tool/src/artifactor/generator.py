"""Post generation logic for Artifactor."""

import json
from pathlib import Path
from typing import Dict, Any

import yaml
from jinja2 import Environment, PackageLoader, select_autoescape

from .models import Article


class PostGenerator:
    """Generates Jekyll HTML posts from Article objects."""

    def __init__(self):
        """Initialize the Jinja2 environment."""
        self.env = Environment(
            loader=PackageLoader("artifactor", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate_post(self, article: Article, output_dir: Path) -> Path:
        """Generate a Jekyll post file from an Article.

        Args:
            article: Article object to convert to a post
            output_dir: Directory where the post will be written (e.g., site/_posts/)

        Returns:
            Path to the generated post file
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / article.filename

        # Render the post content
        content = self.render_post(article)

        # Write with normalized line endings
        output_path.write_text(content, encoding="utf-8")

        return output_path

    def render_post(self, article: Article) -> str:
        """Render a complete Jekyll post with front matter and content.

        Args:
            article: Article to render

        Returns:
            Complete post content as a string
        """
        # Generate YAML front matter in stable order
        front_matter = self._generate_front_matter(article)

        # Render the template
        template = self.env.get_template("post.html.jinja2")
        content = template.render(
            front_matter=front_matter,
            content=article.html,
        )

        return content

    def _generate_front_matter(self, article: Article) -> str:
        """Generate YAML front matter in stable key order.

        Args:
            article: Article to generate front matter from

        Returns:
            YAML front matter as a string (without delimiters)
        """
        # Build front matter dict in stable order
        fm_dict: Dict[str, Any] = {
            "layout": "reprint",
            "title": article.title,
            "date": article.date,
            "canonical_url": article.canonical_url,
            "source": article.source,
        }

        # Add optional fields only if non-empty
        if article.authors:
            fm_dict["authors"] = article.authors
        if article.tags:
            fm_dict["tags"] = article.tags

        # Use PyYAML with stable formatting
        # default_flow_style=False ensures lists use block style (2-space indent)
        # sort_keys=False preserves our insertion order
        yaml_str = yaml.dump(
            fm_dict,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            indent=2,
        )

        return yaml_str.rstrip()

    @staticmethod
    def load_article_from_fixture(fixture_path: Path) -> Article:
        """Load an Article from a JSON fixture file.

        Args:
            fixture_path: Path to JSON fixture file

        Returns:
            Article object
        """
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return Article(**data)
