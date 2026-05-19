from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # PostgreSQL
    database_url: str = "postgresql+asyncpg://postgres:root@localhost:5432/Chatboot"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_enabled: bool = True

    # MSSQL (MSX website DB)
    mssql_server:   str = "localhost"
    mssql_port:     int = 1433
    mssql_database: str = "MSM_GEO_Live"
    mssql_username: str = "sa"
    mssql_password: str = "your_password"

    # Ollama / LocalAI (OpenAI-compatible)
    localai_base_url:        str = "http://localhost:11434/v1"
    localai_timeout:         int = 120
    localai_model:           str = "qwen2.5:7b"
    localai_model_fallback:  str = "qwen2.5:7b"
    localai_model_fast:      str = "qwen2.5:7b"
    localai_model_analysis:  str = "qwen2.5:7b"

    # RAG / Qdrant
    qdrant_url:        str = "http://localhost:6333"
    qdrant_collection: str = "msx_data"
    embedding_model:   str = "nomic-embed-text"

    # Auth
    admin_username:              str = "admin"
    admin_password:              str = "changeme123"
    secret_key:                  str = "msx-secret-key-change-in-production"
    algorithm:                   str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    # App
    app_name:    str       = "MSX Smart Assistant"
    app_version: str       = "1.0.0"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
