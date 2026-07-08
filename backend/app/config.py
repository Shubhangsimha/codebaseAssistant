import logging
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: str = "./data"

    # Optional — warn if absent but do not crash startup
    gemini_api_key: str = ""
    groq_api_key: str = ""

    def model_post_init(self, __context: object) -> None:
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY is not set — AI features will be unavailable")
        if not self.groq_api_key:
            logger.warning("GROQ_API_KEY is not set — Groq fallback will be unavailable")


settings = Settings()
