import json

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite locally, Postgres (Neon) in a deployment. Paste Neon's connection
    # string in as-is -- `sqlalchemy_url` below sorts out the dialect prefix.
    #
    # What must never happen is a deployment quietly running on the container's
    # own filesystem: that is wiped on every redeploy, and losing the recorded
    # consultations is not an acceptable way to discover it.
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

    # Unlocks the consultation-history page, which is the only endpoint that
    # can see across encounters. Unset means that page is disabled, not open --
    # see app/routers/history.py for why that default matters.
    admin_key: str | None = None

    # The AI second opinion is optional and off unless a key is set. Set
    # exactly one of these; the first one found wins, in the order listed in
    # app/ai/factory.py. With none set the feature says so on screen and
    # everything else works normally.
    #
    # Gemini is the default because its free tier is real: no card, and a
    # daily request allowance far above what one doctor testing the tool will
    # get through.
    gemini_api_key: str | None = None
    gemini_api_base: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_model: str = "gemini-3.7-flash"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-opus-5"
    anthropic_effort: str = "medium"

    xai_api_key: str | None = None
    xai_api_base: str = "https://api.x.ai/v1"
    xai_model: str = "grok-4"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def sqlalchemy_url(self) -> str:
        """Names the driver SQLAlchemy should use, whatever Neon handed you.

        Neon (and Railway, and Heroku before them) give out connection strings
        beginning `postgres://` or `postgresql://`. SQLAlchemy 2 refuses the
        first outright and, for the second, reaches for psycopg2 -- which is
        not installed here, because this runs on psycopg 3. Both failures are
        at import time with a message that says nothing about the real cause,
        so the prefix is normalised here rather than left as something a
        person has to know to type correctly at 1am.
        """
        url = self.database_url
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        """Accepts `a, b` or `["a", "b"]`, because both will get typed."""
        raw = self.cors_origins.strip()
        if raw.startswith("["):
            return [str(origin) for origin in json.loads(raw)]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()
