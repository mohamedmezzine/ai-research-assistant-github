from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    gemini_api_key: str
    database_url: str = "postgresql://postgres:postgres@localhost:5433/research_assistant"
    upload_dir: str = "../data/papers"

    # AI Mode: cloud, hybrid, private
    ai_mode: str = "cloud"

    # Cloud settings
    cloud_chat_provider: str = "gemini"
    cloud_chat_model: str = "gemini-1.5-flash"
    cloud_embedding_provider: str = "gemini"
    cloud_embedding_model: str = "text-embedding-004"

    # Local settings
    local_chat_provider: str = "ollama"
    local_chat_model: str = "llama3.1:8b"
    ollama_base_url: str = "http://localhost:11434"
    local_embedding_provider: str = "sentence_transformers"
    local_embedding_model: str = "sentence-transformers/all-mpnet-base-v2"

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
