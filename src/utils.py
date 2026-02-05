"""Utility functions for URL handling and common operations."""

from urllib.parse import urlparse, urlunparse
import re


def extract_domain(url: str) -> str:
    """
    Extract the base domain from a URL.

    Args:
        url: The full URL to parse

    Returns:
        The domain without protocol or path (e.g., 'example.com')

    Examples:
        >>> extract_domain('https://www.example.com/page')
        'example.com'
        >>> extract_domain('https://blog.example.com/post')
        'blog.example.com'
    """
    parsed = urlparse(url)
    domain = parsed.netloc

    # Remove 'www.' prefix if present
    if domain.startswith('www.'):
        domain = domain[4:]

    return domain


def normalize_url(url: str) -> str:
    """
    Normalize a URL for comparison purposes.

    Removes trailing slashes, converts to lowercase, removes fragments,
    and standardizes the scheme.

    Args:
        url: The URL to normalize

    Returns:
        The normalized URL

    Examples:
        >>> normalize_url('https://Example.com/Page/')
        'https://example.com/page'
        >>> normalize_url('http://www.example.com/page#section')
        'https://example.com/page'
    """
    parsed = urlparse(url.lower())

    # Standardize scheme to https
    scheme = 'https'

    # Remove www. from netloc
    netloc = parsed.netloc
    if netloc.startswith('www.'):
        netloc = netloc[4:]

    # Remove trailing slash from path
    path = parsed.path.rstrip('/')

    # Rebuild URL without fragment
    normalized = urlunparse((
        scheme,
        netloc,
        path,
        '',  # params
        parsed.query,  # keep query string
        ''   # no fragment
    ))

    return normalized


def validate_url(url: str) -> bool:
    """
    Validate that a string is a properly formatted URL.

    Args:
        url: The string to validate

    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([
            result.scheme in ('http', 'https'),
            result.netloc,
            '.' in result.netloc  # Must have at least one dot in domain
        ])
    except Exception:
        return False


def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and normalizing.

    Args:
        text: The text to clean

    Returns:
        Cleaned text with normalized whitespace
    """
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length, adding suffix if truncated.

    Args:
        text: The text to truncate
        max_length: Maximum length including suffix
        suffix: String to append if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
