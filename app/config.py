"""Application settings loaded from environment variables."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for Healthcare Claims AI Agent."""

    model_config = {"env_file": ".env", "extra": "ignore"}

    # Anthropic
    anthropic_api_key: str

    # AWS (added later)
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket_name: str = ""

    # App
    environment: str = "local"
    chroma_db_path: str = "./chroma_db"
    app_port: int = 8000
    debug: bool = True


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()