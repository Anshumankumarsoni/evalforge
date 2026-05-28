"""Configuration management using Pydantic Settings (v2 compatible)"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # OpenAI
    openai_api_key: str = ""
    openai_model_default: str = "gpt-4o"

    # Anthropic Claude
    anthropic_api_key: str = ""
    claude_model_default: str = "claude-opus-4-1"

    # Google Gemini
    google_api_key: str = ""
    gemini_model_default: str = "gemini-2.0-flash"

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/evalforge.db"

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # Streamlit Dashboard
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8501

    # Logging
    log_level: str = "INFO"

    # Regression Detection
    regression_threshold: float = 0.05

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


# Global singleton
settings = Settings()
