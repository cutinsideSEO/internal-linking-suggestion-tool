"""Keyword extraction module using RAKE-NLTK."""

from dataclasses import dataclass
from typing import Optional
import re

from rake_nltk import Rake

from .config import Config


@dataclass
class Keyword:
    """A keyword/phrase with its relevance score."""
    phrase: str
    score: float


def _clean_keyword(phrase: str) -> Optional[str]:
    """
    Clean and validate a keyword phrase.

    Args:
        phrase: The raw keyword phrase

    Returns:
        Cleaned phrase, or None if invalid
    """
    # Strip and lowercase
    phrase = phrase.strip().lower()

    # Remove phrases that are just numbers or special characters
    if re.match(r'^[\d\s\W]+$', phrase):
        return None

    # Remove phrases with too many numbers
    digit_ratio = sum(c.isdigit() for c in phrase) / max(len(phrase), 1)
    if digit_ratio > 0.3:
        return None

    # Check length constraints
    if len(phrase) < Config.MIN_KEYWORD_LENGTH or len(phrase) > Config.MAX_KEYWORD_LENGTH:
        return None

    # Check word count
    word_count = len(phrase.split())
    if word_count < Config.MIN_PHRASE_WORDS or word_count > Config.MAX_PHRASE_WORDS:
        return None

    return phrase


def extract_keywords(
    text: str,
    max_keywords: int = None,
    min_score: float = None
) -> list[Keyword]:
    """
    Extract keywords from text using RAKE algorithm.

    Args:
        text: The text content to analyze
        max_keywords: Maximum number of keywords to return (default from config)
        min_score: Minimum score threshold (default from config)

    Returns:
        List of Keyword objects sorted by score (descending)
    """
    if max_keywords is None:
        max_keywords = Config.MAX_KEYWORDS
    if min_score is None:
        min_score = Config.MIN_KEYWORD_SCORE

    # Initialize RAKE with default English stopwords
    rake = Rake(
        min_length=Config.MIN_PHRASE_WORDS,
        max_length=Config.MAX_PHRASE_WORDS,
        include_repeated_phrases=False
    )

    # Extract keywords from text
    rake.extract_keywords_from_text(text)

    # Get ranked phrases with scores
    ranked_phrases = rake.get_ranked_phrases_with_scores()

    # Process and filter keywords
    keywords = []
    seen_phrases = set()

    for score, phrase in ranked_phrases:
        # Clean and validate the phrase
        cleaned = _clean_keyword(phrase)
        if cleaned is None:
            continue

        # Skip duplicates
        if cleaned in seen_phrases:
            continue

        # Check minimum score
        if score < min_score:
            continue

        seen_phrases.add(cleaned)
        keywords.append(Keyword(phrase=cleaned, score=score))

        # Stop if we have enough keywords
        if len(keywords) >= max_keywords:
            break

    return keywords


def extract_keywords_with_context(
    text: str,
    title: str = "",
    headings: list[str] = None,
    max_keywords: int = None
) -> list[Keyword]:
    """
    Extract keywords with additional context from title and headings.

    Keywords found in title or headings get a score boost.

    Args:
        text: Main page text content
        title: Page title
        headings: List of heading texts
        max_keywords: Maximum keywords to return

    Returns:
        List of keywords with boosted scores for prominent terms
    """
    if headings is None:
        headings = []
    if max_keywords is None:
        max_keywords = Config.MAX_KEYWORDS

    # Combine title and headings for context
    context_text = f"{title} {' '.join(headings)}".lower()

    # Extract base keywords
    keywords = extract_keywords(text, max_keywords=max_keywords * 2)

    # Boost scores for keywords found in title/headings
    boosted_keywords = []
    for kw in keywords:
        boost = 1.0
        if kw.phrase in context_text:
            boost = 1.5  # 50% boost for keywords in title/headings

        boosted_keywords.append(Keyword(
            phrase=kw.phrase,
            score=kw.score * boost
        ))

    # Re-sort by boosted score and limit
    boosted_keywords.sort(key=lambda k: k.score, reverse=True)
    return boosted_keywords[:max_keywords]
