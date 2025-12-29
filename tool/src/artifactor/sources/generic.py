"""Generic fallback adapter for content extraction."""

import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from .base import SourceAdapter, AdapterMetadata
from artifactor.models import Article


class GenericAdapter(SourceAdapter):
    """Generic fallback adapter for any website."""

    def can_handle(self, url: str) -> bool:
        """Generic adapter can handle any URL."""
        return True

    def get_metadata(self) -> AdapterMetadata:
        """Return metadata for generic adapter."""
        return AdapterMetadata(
            name="generic",
            description="Generic fallback for any website",
            priority=10,
            match_patterns=["*"],
        )

    def extract(self, url: str, html: str) -> Article:
        """Extract article content using generic extraction."""
        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title = self._extract_title(soup)

        # Extract canonical URL
        canonical_url = self._extract_canonical(soup, url)

        # Extract date (may fail)
        try:
            date = self._extract_date(soup)
        except ValueError as e:
            raise ValueError(
                f"Could not extract date from {url}. "
                "Please add --default-date YYYY-MM-DD option or verify the URL."
            ) from e

        # Extract authors
        authors = self._extract_authors(soup)

        # Generate slug from URL
        slug = self._generate_slug(url, title)

        # Extract site name for source
        source = self._extract_source(soup, url)

        # Extract main article HTML
        article_html = self._extract_article_html(soup)

        return Article(
            title=title,
            date=date,
            slug=slug,
            canonical_url=canonical_url,
            source=source,
            html=article_html,
            authors=authors,
            tags=[],
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract title from page."""
        # Try og:title meta tag
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        # Try first H1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text().strip()

        # Fallback to document title
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text().strip()
            # Try to remove site name suffix
            title = re.sub(r"\s*[||-]\s+.*$", "", title)
            return title

        raise ValueError("Could not extract title from page")

    def _extract_canonical(self, soup: BeautifulSoup, fallback_url: str) -> str:
        """Extract canonical URL."""
        # Try link rel="canonical"
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            return canonical["href"].strip()

        # Try og:url
        og_url = soup.find("meta", property="og:url")
        if og_url and og_url.get("content"):
            return og_url["content"].strip()

        # Fallback to input URL
        return fallback_url

    def _extract_date(self, soup: BeautifulSoup) -> str:
        """Extract publication date from page."""
        # Try article:published_time meta tag
        published_time = soup.find("meta", property="article:published_time")
        if published_time and published_time.get("content"):
            try:
                dt = dateparser.parse(published_time["content"])
                if dt:
                    return dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        # Try <time> tags
        time_tag = soup.find("time")
        if time_tag:
            datetime_attr = time_tag.get("datetime")
            if datetime_attr:
                try:
                    dt = dateparser.parse(datetime_attr)
                    if dt:
                        return dt.strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    pass

        raise ValueError("Could not extract date from page")

    def _extract_authors(self, soup: BeautifulSoup) -> list[str]:
        """Extract author names from page."""
        authors = []

        # Try meta name="author"
        author_meta = soup.find("meta", attrs={"name": "author"})
        if author_meta and author_meta.get("content"):
            content = author_meta["content"].strip()
            if content and content.lower() not in ("unknown", "admin"):
                authors.append(content)

        return authors

    def _extract_source(self, soup: BeautifulSoup, url: str) -> str:
        """Extract source/site name."""
        # Try og:site_name
        site_name = soup.find("meta", property="og:site_name")
        if site_name and site_name.get("content"):
            return site_name["content"].strip()

        # Fallback to domain name
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove www. prefix
        domain = re.sub(r"^www\.", "", domain)
        # Capitalize first letter
        return domain.split(".")[0].capitalize()

    def _generate_slug(self, url: str, title: str) -> str:
        """Generate slug from URL or title."""
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]

        # Use last path component if it looks reasonable
        if path_parts:
            last_part = path_parts[-1]
            # Remove file extensions
            last_part = re.sub(r"\.(html|htm|php|asp|aspx)$", "", last_part)
            if last_part and len(last_part) > 3:
                return last_part

        # Fallback: slugify title
        slug = title.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)
        slug = slug.strip("-")
        return slug[:100]  # Limit length

    def _extract_article_html(self, soup: BeautifulSoup) -> str:
        """Extract main article HTML content."""
        # Try to find article or main tag
        article = soup.find("article")
        if not article:
            article = soup.find("main")
        if not article:
            # Try to find div with role="main"
            article = soup.find("div", role="main")
        if not article:
            # Fallback to body, but strip navigation elements
            article = soup.find("body")

        if not article:
            raise ValueError("Could not find article content in page")

        # Make a copy to avoid modifying the original
        article = article.__copy__()

        # Remove unwanted elements
        self._clean_article(article)

        # Get HTML content
        html = str(article)

        # Normalize whitespace and line endings
        html = re.sub(r"\r\n", "\n", html)
        html = re.sub(r"\r", "\n", html)

        return html.strip()

    def _clean_article(self, article):
        """Remove unwanted elements from article HTML."""
        # Remove scripts, styles, nav, header, footer
        for tag in article.find_all(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        # Remove common unwanted elements by class/id patterns
        unwanted_patterns = [
            "nav",
            "menu",
            "sidebar",
            "footer",
            "header",
            "advertisement",
            "ads",
            "social",
            "share",
            "comments",
        ]

        for pattern in unwanted_patterns:
            # Remove by class
            for elem in article.find_all(class_=re.compile(pattern, re.I)):
                elem.decompose()
            # Remove by id
            for elem in article.find_all(id=re.compile(pattern, re.I)):
                elem.decompose()
