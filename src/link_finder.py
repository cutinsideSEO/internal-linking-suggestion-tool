"""Main orchestration module for finding internal linking opportunities using Gemini AI."""

import logging
from dataclasses import dataclass, field
from typing import Optional, Callable

from .config import Config
from .dataforseo_client import DataForSEOClient, APIError, SearchResult
from .gemini_extractor import extract_anchor_texts, AnchorTextSuggestion, GeminiError
from .scraper import scrape_page, ScrapingError, PageContent
from .utils import normalize_url, validate_url

logger = logging.getLogger(__name__)


@dataclass
class TargetURL:
    """A target URL found for an anchor text."""
    url: str
    title: str
    position: int


@dataclass
class LinkSuggestion:
    """A suggested internal link with multiple target options."""
    anchor_text: str
    relevance_score: float
    reasoning: str
    target_urls: list[TargetURL] = field(default_factory=list)


class InternalLinkFinder:
    """Finds internal linking opportunities using Gemini AI and DataForSEO."""

    def __init__(self, client: DataForSEOClient = None, verbose: bool = False):
        """
        Initialize the link finder.

        Args:
            client: DataForSEO client instance (creates one if not provided)
            verbose: Enable verbose logging
        """
        self.client = client or DataForSEOClient()
        self.verbose = verbose

        if verbose:
            logging.basicConfig(level=logging.INFO)

    def find_opportunities(
        self,
        source_url: str,
        on_status_update: Callable[[str], None] = None,
        on_keyword_progress: Callable[[int, int, str], None] = None
    ) -> tuple[list[LinkSuggestion], list[str]]:
        """
        Find internal linking opportunities for a URL using Gemini AI.

        Args:
            source_url: The URL to find internal links for
            on_status_update: Callback for status updates (status_message)
            on_keyword_progress: Callback for keyword progress (current, total, keyword)

        Returns:
            Tuple of (list of LinkSuggestion objects, list of error messages)

        Raises:
            ScrapingError: If the source URL cannot be scraped
            ValueError: If the URL is invalid
        """
        # Validate URL
        if not validate_url(source_url):
            raise ValueError(f"Invalid URL: {source_url}")

        errors = []
        suggestions = []

        def update_status(msg: str):
            logger.info(msg)
            if on_status_update:
                on_status_update(msg)

        # Step 1: Scrape the source page
        update_status("Scraping page content...")
        page_content = scrape_page(source_url)
        normalized_source = normalize_url(source_url)

        # Step 2: Use Gemini AI to extract anchor text suggestions
        update_status("Analyzing content with Gemini AI...")
        try:
            anchor_suggestions = extract_anchor_texts(
                content=page_content.text,
                page_title=page_content.title,
                domain=page_content.domain,
                max_suggestions=Config.MAX_KEYWORDS
            )
        except GeminiError as e:
            errors.append(f"Gemini AI error: {str(e)}")
            return suggestions, errors

        if not anchor_suggestions:
            errors.append("Gemini could not extract any anchor text suggestions")
            return suggestions, errors

        update_status(f"Found {len(anchor_suggestions)} anchor text suggestions")

        # Step 3: Search DataForSEO for each anchor text (exactly 10 searches)
        update_status("Searching for target pages...")

        for i, anchor in enumerate(anchor_suggestions[:Config.MAX_KEYWORDS]):
            if on_keyword_progress:
                on_keyword_progress(i + 1, len(anchor_suggestions), anchor.text)

            logger.info(f"Searching for: {anchor.text}")

            suggestion = LinkSuggestion(
                anchor_text=anchor.text,
                relevance_score=anchor.relevance_score,
                reasoning=anchor.reasoning,
                target_urls=[]
            )

            try:
                results = self.client.search_site(
                    domain=page_content.domain,
                    keyword=anchor.text,
                    depth=Config.SEARCH_DEPTH
                )

                # Filter and add up to MAX_TARGET_URLS_PER_KEYWORD target URLs
                urls_added = 0
                for result in results:
                    # Skip the source URL
                    if normalize_url(result.url) == normalized_source:
                        continue

                    suggestion.target_urls.append(TargetURL(
                        url=result.url,
                        title=result.title,
                        position=result.position
                    ))

                    urls_added += 1
                    if urls_added >= Config.MAX_TARGET_URLS_PER_KEYWORD:
                        break

            except APIError as e:
                error_msg = f"API error for '{anchor.text}': {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)

            # Add suggestion even if no URLs found (to show what Gemini suggested)
            suggestions.append(suggestion)

        update_status("Analysis complete!")
        return suggestions, errors


def find_internal_links(
    url: str,
    verbose: bool = False,
    on_status_update: Callable[[str], None] = None
) -> tuple[list[LinkSuggestion], list[str]]:
    """
    Convenience function to find internal linking opportunities.

    Args:
        url: The URL to analyze
        verbose: Enable verbose output
        on_status_update: Callback for status updates

    Returns:
        Tuple of (suggestions, errors)
    """
    finder = InternalLinkFinder(verbose=verbose)
    return finder.find_opportunities(
        source_url=url,
        on_status_update=on_status_update
    )
