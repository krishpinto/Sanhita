from functools import lru_cache

from app.ai.base import SecondOpinionProvider
from app.ai.noop_provider import NoopProvider
from app.ai.xai_provider import XaiProvider
from app.config import settings


@lru_cache
def get_ai_provider() -> SecondOpinionProvider:
    if settings.xai_api_key:
        return XaiProvider(settings.xai_api_key, settings.xai_api_base, settings.xai_model)
    return NoopProvider()
