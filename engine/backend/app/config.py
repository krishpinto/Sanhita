import json

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Local default is a file next to the code. In a deployment this must point
    # at a mounted volume (e.g. sqlite:////data/vitalis.db) -- a container's own
    # filesystem is wiped on every redeploy, and taking the recorded
    # consultations with it is not an acceptable way to find that out.
    database_url: str = "sqlite:///./vitalis.db"

    # The web app is served from a different origin than the API (Vercel and
    # Railway respectively), so the browser will not talk to the API at all
    # unless the API names the app's origin here.
    #
    # Deliberately a plain string, not list[str]: for a list field
    # pydantic-settings runs json.loads() on the environment value before any
    # validator can see it, so a perfectly reasonable
    # `CORS_ORIGINS=https://a.vercel.app` crashes the process on boot with a
    # JSON error. Typing JSON into a hosting dashboard's text box is not a
    # thing anyone should have to know to do.
    cors_origins: str = "http://localhost:5173"

    # Every Vercel preview build gets its own hostname, so they cannot be
    # listed one by one. A pattern like https://.*\\.vercel\\.app covers them.
    cors_origin_regex: str | None = None

    xai_api_key: str | None = None
    xai_api_base: str = "https://api.x.ai/v1"
    xai_model: str = "grok-4"

    @property
    def cors_origin_list(self) -> list[str]:
        """Accepts `a, b` or `["a", "b"]`, because both will get typed."""
        raw = self.cors_origins.strip()
        if raw.startswith("["):
            return [str(origin) for origin in json.loads(raw)]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()
