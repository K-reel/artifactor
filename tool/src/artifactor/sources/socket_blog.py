"""Socket blog adapter for content extraction."""

import re
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from .base import SourceAdapter, AdapterMetadata
from artifactor.models import Article


class SocketBlogAdapter(SourceAdapter):
    """Adapter for Socket.dev blog posts."""

    def can_handle(self, url: str) -> bool:
        """Check if URL is from Socket blog."""
        parsed = urlparse(url)
        return parsed.netloc in ("socket.dev", "www.socket.dev") and "/blog/" in parsed.path

    def get_metadata(self) -> AdapterMetadata:
        """Return metadata for Socket blog adapter."""
        return AdapterMetadata(
            name="socket",
            description="Socket.dev security blog posts",
            priority=80,
            match_patterns=["socket.dev/blog/*", "www.socket.dev/blog/*"],
        )

    def extract(self, url: str, html: str) -> Article:
        """Extract article content from Socket blog HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title = self._extract_title(soup)

        # Extract canonical URL
        canonical_url = self._extract_canonical(soup, url)

        # Extract date
        date = self._extract_date(soup)

        # Extract authors
        authors = self._extract_authors(soup)

        # Generate slug from URL
        slug = self._generate_slug(url, title)

        # Extract main article HTML
        article_html = self._extract_article_html(soup)

        return Article(
            title=title,
            date=date,
            slug=slug,
            canonical_url=canonical_url,
            source="Socket",
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
            # Remove " | Socket" or similar suffixes
            title = title_tag.get_text().strip()
            title = re.sub(r"\s*[||-]\s*Socket.*$", "", title)
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

        # Try to find date in common patterns
        # Look for <time> tags
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

            # Try parsing the text content
            time_text = time_tag.get_text().strip()
            try:
                dt = dateparser.parse(time_text)
                if dt:
                    return dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                pass

        # Look for date patterns in text (e.g., "May 21, 2025")
        # Search in article or main content
        article = soup.find("article") or soup.find("main") or soup
        text = article.get_text()

        # Common date patterns
        date_patterns = [
            r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
            r"\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    dt = dateparser.parse(match.group(0))
                    if dt:
                        return dt.strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    pass

        raise ValueError(
            "Could not extract date from page. "
            "Please add --default-date YYYY-MM-DD option or verify the URL."
        )

    def _extract_authors(self, soup: BeautifulSoup) -> list[str]:
        """Extract author names from page."""
        authors = []

        # Try meta name="author"
        author_meta = soup.find("meta", attrs={"name": "author"})
        if author_meta and author_meta.get("content"):
            authors.append(author_meta["content"].strip())
            return authors

        # Try to find author in article metadata or byline
        # Look for common patterns like "By Author Name" or class="author"
        author_elements = soup.find_all(class_=re.compile(r"author|byline", re.I))
        for elem in author_elements:
            text = elem.get_text().strip()
            # Remove "By" prefix if present
            text = re.sub(r"^By\s+", "", text, flags=re.I)
            if text and len(text) < 100:  # Sanity check
                authors.append(text)
                break

        return authors

    def _generate_slug(self, url: str, title: str) -> str:
        """Generate slug from URL or title."""
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]

        # Use last path component if it looks reasonable
        if path_parts:
            last_part = path_parts[-1]
            # Remove file extensions
            last_part = re.sub(r"\.(html|htm|php)$", "", last_part)
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
        article = None

        # Strategy 1: Look for semantic content classes (prose, article-content, etc.)
        # Socket.dev uses <div class="prose"> for main article body
        semantic_selectors = [
            {"class": "prose"},
            {"class": re.compile(r"article-content", re.I)},
            {"class": re.compile(r"post-content", re.I)},
            {"class": re.compile(r"entry-content", re.I)},
        ]

        for selector in semantic_selectors:
            article = soup.find("div", **selector)
            if article:
                break

        # Strategy 2: Find H1 and score ancestor containers
        if not article:
            h1 = soup.find("h1")
            if h1:
                article = self._find_content_container(h1, soup)

        # Strategy 3: Fallback to traditional selectors
        if not article:
            article = soup.find("article")
            # Filter out small articles (likely cards/teasers, not main content)
            if article:
                text_len = len(article.get_text(strip=True))
                if text_len < 500:  # Too small to be main article
                    article = None

        if not article:
            article = soup.find("main")

        if not article:
            # Try to find div with class containing "post" or "article"
            article = soup.find("div", class_=re.compile(r"(post|article|content)-", re.I))

        if not article:
            raise ValueError("Could not find article content in page")

        # Make a copy to avoid modifying the original
        article = article.__copy__()

        # Remove unwanted sections
        self._clean_article(article)

        # Get HTML content
        html = str(article)

        # Normalize whitespace and line endings
        html = re.sub(r"\r\n", "\n", html)
        html = re.sub(r"\r", "\n", html)

        return html.strip()

    def _find_content_container(self, h1, soup: BeautifulSoup):
        """Find the best container for article content by scoring ancestors of H1."""
        candidates = []

        # Walk up the DOM tree from H1
        parent = h1.parent
        depth = 0
        max_depth = 10

        while parent and depth < max_depth and parent.name != "[document]":
            # Score this container
            score = 0
            text_len = len(parent.get_text(strip=True))

            # Prefer containers with substantial text (5k-20k chars is typical for articles)
            if 3000 < text_len < 50000:
                score += 10
            elif text_len > 1000:
                score += 5

            # Prefer semantic tags
            if parent.name in ("article", "main", "section"):
                score += 3
            elif parent.name == "div":
                score += 1

            # Prefer containers with content-related classes
            classes = parent.get("class", [])
            class_str = " ".join(classes).lower()
            if any(keyword in class_str for keyword in ["content", "article", "post", "body"]):
                score += 5

            # Penalize containers with too many children (likely navigation/layout)
            child_count = len(parent.find_all(recursive=False))
            if child_count > 10:
                score -= 2

            # Penalize containers that are too large (likely body or root)
            if text_len > 50000:
                score -= 5

            candidates.append({
                "element": parent,
                "score": score,
                "text_len": text_len,
                "depth": depth
            })

            parent = parent.parent
            depth += 1

        # Sort by score (highest first), then by depth (shallowest first)
        candidates.sort(key=lambda x: (x["score"], -x["depth"]), reverse=True)

        # Return the best candidate if any
        if candidates and candidates[0]["score"] > 0:
            return candidates[0]["element"]

        return None

    def _clean_article(self, article):
        """Remove unwanted elements from article HTML."""
        # Remove scripts and styles
        for tag in article.find_all(["script", "style"]):
            tag.decompose()

        # Remove newsletter subscribe sections
        for elem in article.find_all(string=re.compile(r"subscribe\s+to\s+(our\s+)?newsletter", re.I)):
            parent = elem.find_parent()
            if parent:
                # Remove the parent container
                container = parent.find_parent(["div", "section", "aside"])
                if container:
                    container.decompose()
                else:
                    parent.decompose()

        # Remove "Related posts" sections
        for elem in article.find_all(string=re.compile(r"related\s+posts?", re.I)):
            parent = elem.find_parent()
            if parent:
                container = parent.find_parent(["div", "section", "aside"])
                if container:
                    container.decompose()
                else:
                    parent.decompose()

        # Remove common unwanted classes
        unwanted_classes = [
            "newsletter",
            "subscribe",
            "related-posts",
            "share-buttons",
            "social-share",
        ]
        for class_name in unwanted_classes:
            for elem in article.find_all(class_=re.compile(class_name, re.I)):
                elem.decompose()
