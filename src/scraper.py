"""Web scraping module for extracting content from URLs."""

from dataclasses import dataclass
from typing import Optional
import requests
from bs4 import BeautifulSoup

from .utils import extract_domain, clean_text


class ScrapingError(Exception):
    """Exception raised when scraping fails."""
    pass


@dataclass
class PageContent:
    """Data class holding scraped page content."""
    url: str
    domain: str
    title: str
    text: str
    headings: list[str]


def fetch_url(url: str, timeout: int = 30) -> str:
    """
    Fetch HTML content from a URL.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds

    Returns:
        The HTML content as a string

    Raises:
        ScrapingError: If the request fails
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout:
        raise ScrapingError(f"Request timed out after {timeout} seconds: {url}")
    except requests.exceptions.HTTPError as e:
        raise ScrapingError(f"HTTP error {e.response.status_code}: {url}")
    except requests.exceptions.RequestException as e:
        raise ScrapingError(f"Failed to fetch URL: {url} - {str(e)}")


def extract_text_content(html: str) -> str:
    """
    Extract meaningful text content from HTML.

    Extracts text from paragraphs, headings, list items, and other
    content elements while ignoring scripts, styles, and navigation.

    Args:
        html: The HTML content to parse

    Returns:
        Cleaned text content
    """
    soup = BeautifulSoup(html, 'lxml')

    # Remove unwanted elements
    for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer',
                                   'aside', 'form', 'noscript', 'iframe']):
        element.decompose()

    # Extract text from content elements
    content_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th',
                    'article', 'section', 'main', 'blockquote']

    text_parts = []
    for tag in soup.find_all(content_tags):
        text = tag.get_text(separator=' ', strip=True)
        if text and len(text) > 10:  # Skip very short text
            text_parts.append(text)

    combined_text = ' '.join(text_parts)
    return clean_text(combined_text)


def get_page_title(html: str) -> str:
    """
    Extract the page title from HTML.

    Args:
        html: The HTML content to parse

    Returns:
        The page title, or empty string if not found
    """
    soup = BeautifulSoup(html, 'lxml')

    # Try title tag first
    title_tag = soup.find('title')
    if title_tag and title_tag.string:
        return clean_text(title_tag.string)

    # Fall back to h1
    h1_tag = soup.find('h1')
    if h1_tag:
        return clean_text(h1_tag.get_text())

    return ""


def get_headings(html: str) -> list[str]:
    """
    Extract all headings from HTML.

    Args:
        html: The HTML content to parse

    Returns:
        List of heading texts
    """
    soup = BeautifulSoup(html, 'lxml')
    headings = []

    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        text = clean_text(tag.get_text())
        if text and len(text) > 3:
            headings.append(text)

    return headings


def scrape_page(url: str) -> PageContent:
    """
    Scrape a URL and extract all relevant content.

    Args:
        url: The URL to scrape

    Returns:
        PageContent object with extracted content

    Raises:
        ScrapingError: If scraping fails
    """
    html = fetch_url(url)

    title = get_page_title(html)
    text = extract_text_content(html)
    headings = get_headings(html)
    domain = extract_domain(url)

    if not text:
        raise ScrapingError(f"No extractable content found at: {url}")

    return PageContent(
        url=url,
        domain=domain,
        title=title,
        text=text,
        headings=headings
    )
