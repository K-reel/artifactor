"""HTTP fetching functionality for Artifactor."""

from typing import Tuple
import httpx


class FetchResult:
    """Result of fetching a URL."""

    def __init__(
        self,
        url: str,
        final_url: str,
        status_code: int,
        html: str,
        headers: dict,
    ):
        self.url = url
        self.final_url = final_url
        self.status_code = status_code
        self.html = html
        self.headers = headers

    @property
    def success(self) -> bool:
        """Check if fetch was successful."""
        return 200 <= self.status_code < 300


def fetch_url(
    url: str,
    timeout: int = 20,
    user_agent: str = "Artifactor/0.1 (+https://github.com/user/artifactor)",
) -> FetchResult:
    """Fetch a URL and return the result.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        user_agent: User-Agent header value

    Returns:
        FetchResult with URL, final URL (after redirects), status code, HTML, and headers

    Raises:
        httpx.HTTPError: If the request fails
    """
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()

        return FetchResult(
            url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            html=response.text,
            headers=dict(response.headers),
        )
