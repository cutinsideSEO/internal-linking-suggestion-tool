"""Configuration management for the Internal Linking Tool."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Config:
    """Configuration settings loaded from environment variables."""

    # DataForSEO API Credentials
    DATAFORSEO_LOGIN: str = os.getenv("DATAFORSEO_LOGIN", "")
    DATAFORSEO_PASSWORD: str = os.getenv("DATAFORSEO_PASSWORD", "")

    # Google Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # API Settings
    API_BASE_URL: str = "https://api.dataforseo.com/v3"
    LOCATION_CODE: int = int(os.getenv("LOCATION_CODE", "2840"))  # United States
    LANGUAGE_CODE: str = os.getenv("LANGUAGE_CODE", "en")

    # Keyword/Anchor Text Settings (exactly 10 for optimized API usage)
    MAX_KEYWORDS: int = 10
    MAX_TARGET_URLS_PER_KEYWORD: int = 3

    # Search Settings
    SEARCH_DEPTH: int = int(os.getenv("SEARCH_DEPTH", "10"))
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

    # Retry Settings
    MAX_RETRIES: int = 3
    BASE_RETRY_DELAY: float = 1.0
    MAX_RETRY_DELAY: float = 60.0

    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present."""
        if not cls.DATAFORSEO_LOGIN or not cls.DATAFORSEO_PASSWORD:
            raise ValueError(
                "DataForSEO credentials not found. "
                "Please set DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD in .env file."
            )
        if not cls.GEMINI_API_KEY:
            raise ValueError(
                "Gemini API key not found. "
                "Please set GEMINI_API_KEY in .env file."
            )
        return True
