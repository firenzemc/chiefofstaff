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

    # Storage
    audit_db_path: str = "mainframe_audit.db"
    memory_db_path: str = "mainframe_memory.db"

    # Approval whitelist — comma-separated list of trusted approver names
    approvers: str = ""

    # Approval timeout in hours (default 24h)
    approval_timeout_hours: int = 24

    @property
    def approver_list(self) -> list[str]:
        """Parsed list of allowed approver identities."""
        if not self.approvers.strip():
            return []
        return [a.strip().lower() for a in self.approvers.split(",") if a.strip()]


# Singleton — import ``settings`` wherever you need config.
settings = Settings()
