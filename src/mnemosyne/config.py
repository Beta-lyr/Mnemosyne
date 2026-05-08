"""Application configuration management."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = ""

    # Embedding
    embedding_provider: str = "local"
    embedding_model: str = "BAAI/bge-m3"

    # Database
    database_url: str = "postgresql://mnemosyne:password@localhost:5432/mnemosyne"
    redis_url: str = "redis://localhost:6379/0"

    # Image generation (unified abstraction)
    image_provider: str = "replicate"       # replicate|fal|stability|huggingface|openai-compatible
    image_api_key: str = ""                 # unified API key (preferred)
    image_base_url: str = ""                # custom endpoint URL
    image_model: str = ""                   # model name (provider default if empty)
    replicate_api_token: str = ""           # legacy: Replicate token
    fal_key: str = ""                       # legacy: FAL key

    # Audio generation (unified abstraction)
    audio_provider: str = "edge-tts"        # edge-tts|elevenlabs|huggingface|openai-compatible
    audio_api_key: str = ""
    audio_base_url: str = ""
    audio_model: str = ""

    # Video generation (unified abstraction)
    video_provider: str = "replicate"       # replicate|huggingface|luma
    video_api_key: str = ""
    video_base_url: str = ""
    video_model: str = ""

    # S3-compatible object storage (optional, falls back to local)
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_prefix: str = "mnemosyne/uploads"

    # Web
    web_host: str = "0.0.0.0"
    web_port: int = 8080
    secret_key: str = "change-me-to-a-random-string"

    # Proactive trigger
    max_daily_messages: int = 2
    cooldown_minutes: int = 10
    quiet_hours_start: int = 0
    quiet_hours_end: int = 7

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
