"""DataForSEO API client for searching internal pages."""

import base64
import time
from dataclasses import dataclass
from functools import wraps
from typing import Callable, Optional

import requests
from ratelimit import limits, sleep_and_retry

from .config import Config


class APIError(Exception):
    """Base exception for DataForSEO API errors."""
    pass


class AuthenticationError(APIError):
    """Invalid API credentials."""
    pass


class RateLimitError(APIError):
    """API rate limit exceeded."""
    pass


@dataclass
class SearchResult:
    """A single search result from DataForSEO."""
    url: str
    title: str
    position: int
    snippet: str


def retry_with_backoff(
    max_retries: int = None,
    base_delay: float = None,
    max_delay: float = None
) -> Callable:
    """
    Decorator for retrying failed API calls with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
    """
    if max_retries is None:
        max_retries = Config.MAX_RETRIES
    if base_delay is None:
        base_delay = Config.BASE_RETRY_DELAY
    if max_delay is None:
        max_delay = Config.MAX_RETRY_DELAY

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        time.sleep(delay)
                except requests.exceptions.RequestException as e:
                    last_exception = APIError(f"Request failed: {str(e)}")
                    if attempt < max_retries:
                        time.sleep(base_delay)

            raise last_exception

        return wrapper
    return decorator


class DataForSEOClient:
    """Client for interacting with DataForSEO SERP API."""

    BASE_URL = "https://api.dataforseo.com/v3"

    def __init__(self, login: str = None, password: str = None):
        """
        Initialize the DataForSEO client.

        Args:
            login: DataForSEO login (default from config)
            password: DataForSEO password (default from config)
        """
        if login is None:
            login = Config.DATAFORSEO_LOGIN
        if password is None:
            password = Config.DATAFORSEO_PASSWORD

        if not login or not password:
            raise AuthenticationError(
                "DataForSEO credentials not configured. "
                "Set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD in .env file."
            )

        # Create session with authentication headers
        self.session = requests.Session()
        credentials = base64.b64encode(f"{login}:{password}".encode()).decode()
        self.session.headers.update({
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json"
        })

    @sleep_and_retry
    @limits(calls=30, period=60)  # 30 calls per minute
    @retry_with_backoff()
    def search_site(
        self,
        domain: str,
        keyword: str,
        depth: int = None,
        location_code: int = None,
        language_code: str = None
    ) -> list[SearchResult]:
        """
        Search for a keyword within a specific domain.

        Uses the site: operator to limit results to the given domain.

        Args:
            domain: The domain to search within (e.g., 'example.com')
            keyword: The keyword to search for
            depth: Number of results to retrieve (default from config)
            location_code: Google location code (default from config)
            language_code: Language code (default from config)

        Returns:
            List of SearchResult objects

        Raises:
            APIError: If the API request fails
            AuthenticationError: If credentials are invalid
            RateLimitError: If rate limit is exceeded
        """
        if depth is None:
            depth = Config.SEARCH_DEPTH
        if location_code is None:
            location_code = Config.LOCATION_CODE
        if language_code is None:
            language_code = Config.LANGUAGE_CODE

        endpoint = f"{self.BASE_URL}/serp/google/organic/live/advanced"

        # Build site-specific search query
        search_query = f'site:{domain} "{keyword}"'

        payload = [{
            "keyword": search_query,
            "location_code": location_code,
            "language_code": language_code,
            "depth": depth,
            "device": "desktop"
        }]

        response = self.session.post(endpoint, json=payload)

        # Handle HTTP errors
        if response.status_code == 401:
            raise AuthenticationError("Invalid DataForSEO credentials")
        if response.status_code == 429:
            raise RateLimitError("API rate limit exceeded")

        response.raise_for_status()

        return self._parse_response(response.json())

    def _parse_response(self, data: dict) -> list[SearchResult]:
        """
        Parse API response into SearchResult objects.

        Args:
            data: The API response JSON

        Returns:
            List of SearchResult objects

        Raises:
            APIError: If the API returns an error status
        """
        # Check top-level status
        if data.get("status_code") != 20000:
            raise APIError(
                f"API error: {data.get('status_message', 'Unknown error')}"
            )

        results = []

        for task in data.get("tasks", []):
            # Check task-level status
            task_status = task.get("status_code")
            if task_status != 20000:
                # Skip failed tasks but don't raise
                continue

            for result in task.get("result", []):
                for item in result.get("items", []):
                    # Only process organic results
                    if item.get("type") != "organic":
                        continue

                    results.append(SearchResult(
                        url=item.get("url", ""),
                        title=item.get("title", ""),
                        position=item.get("rank_absolute", 0),
                        snippet=item.get("description", "")
                    ))

        return results

    def check_balance(self) -> dict:
        """
        Check the account balance and limits.

        Returns:
            Dictionary with balance information

        Raises:
            APIError: If the request fails
        """
        endpoint = f"{self.BASE_URL}/appendix/user_data"
        response = self.session.get(endpoint)
        response.raise_for_status()
        return response.json()
