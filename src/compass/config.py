"""Configuration management for Compass RAG."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API
    api_title: str = "Compass RAG"
    api_version: str = "0.0.1"
    debug: bool = False

    # LLM Provider
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    reasoning_model: str = "deepseek-v4"
    summarization_model: str = "deepseek-v4"

    # Indexing
    docs_root: str = "docs"
    atlas_path: str = ".atlas"
    index_json_path: str = ".atlas/index.json"

    # Budget constraints
    max_tool_calls_per_query: int = 20
    max_file_reads_per_query: int = 8

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
