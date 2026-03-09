"""
Application configuration loaded from environment variables.

All settings use the ``MAINFRAME_`` prefix.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Mainframe application."""

    model_config = SettingsConfigDict(env_prefix="MAINFRAME_")

    # LLM
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"

    # Server
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False


# Singleton — import ``settings`` wherever you need config.
settings = Settings()
