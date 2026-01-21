"""
Application configuration using Pydantic Settings.
Loads environment variables for Supabase and database connection.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # Application
    app_name: str = "PromptDa API"
    debug: bool = False
    
    # Supabase Configuration
    supabase_url: str
    supabase_jwt_secret: str
    
    # Database
    database_url: str  # postgresql+asyncpg://user:pass@host:port/db
    
    # CORS Origins (comma-separated)
    cors_origins: str = "http://localhost:3000"
    
    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance to avoid reloading env on each call."""
    return Settings()
