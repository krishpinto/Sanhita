from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./vitalis.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    xai_api_key: str | None = None
    xai_api_base: str = "https://api.x.ai/v1"
    xai_model: str = "grok-4"


settings = Settings()
