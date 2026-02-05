"""Gemini AI-powered anchor text extraction module."""

import json
import re
from dataclasses import dataclass

from google import genai
from google.genai import types

from .config import Config


class GeminiError(Exception):
    """Exception raised when Gemini API fails."""
    pass


@dataclass
class AnchorTextSuggestion:
    """A suggested anchor text with relevance score."""
    text: str
    relevance_score: float
    reasoning: str


def get_client() -> genai.Client:
    """Get a configured Gemini client."""
    api_key = Config.GEMINI_API_KEY
    if not api_key:
        raise GeminiError("Gemini API key not configured")
    return genai.Client(api_key=api_key)


def extract_anchor_texts(
    content: str,
    page_title: str = "",
    domain: str = "",
    max_suggestions: int = 10
) -> list[AnchorTextSuggestion]:
    """
    Use Gemini AI to extract intelligent anchor text suggestions.
    Optimized prompt for minimal token usage.
    """
    client = get_client()

    # Truncate content to save tokens
    max_content_length = 15000
    if len(content) > max_content_length:
        content = content[:max_content_length]

    prompt = f"""Analyze this page from {domain} (title: "{page_title}") and return exactly {max_suggestions} anchor text candidates for internal linking. Pick terms that likely have their own page on this domain.

Content:
{content}

Return ONLY a JSON array:
[{{"anchor_text":"term","relevance_score":0.8,"reasoning":"why"}}]"""

    try:
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1024,
            )
        )

        response_text = response.text.strip()

        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if not json_match:
            raise GeminiError(f"Could not parse Gemini response")

        suggestions_data = json.loads(json_match.group())

        suggestions = []
        for item in suggestions_data[:max_suggestions]:
            text = item.get("anchor_text", "").strip()
            if text:
                suggestions.append(AnchorTextSuggestion(
                    text=text,
                    relevance_score=float(item.get("relevance_score", 0.5)),
                    reasoning=item.get("reasoning", "")
                ))

        return suggestions

    except json.JSONDecodeError as e:
        raise GeminiError(f"Failed to parse Gemini response as JSON: {str(e)}")
    except GeminiError:
        raise
    except Exception as e:
        raise GeminiError(f"Gemini error: {str(e)}")
