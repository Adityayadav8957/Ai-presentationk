from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/ai_presentation"
    redis_url: str = "redis://localhost:6379/0"

    default_llm_provider: str = "siliconflow"
    default_image_provider: str = "siliconflow"

    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"

    anthropic_api_key: str | None = None

    siliconflow_api_key: str | None = None
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"

    ollama_base_url: str = "http://localhost:11434/v1"

    frontend_render_url: str = "http://localhost:3000"
    public_backend_url: str = "http://localhost:8000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
