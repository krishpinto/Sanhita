from functools import lru_cache

from app.ai.base import SecondOpinionProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.noop_provider import NoopProvider
from app.ai.xai_provider import XaiProvider
from app.config import settings


@lru_cache
def get_ai_provider() -> SecondOpinionProvider:
    """Whichever key is set, in this order. No key is a supported state, not
    a misconfiguration -- the tool routes patients without an AI and always
    has."""
    if settings.gemini_api_key:
        return GeminiProvider(settings.gemini_api_key, settings.gemini_api_base, settings.gemini_model)
    if settings.anthropic_api_key:
        # Imported here, not at module scope: the anthropic SDK is the one
        # provider that needs a package installed, and a deployment running
        # on Gemini should not fail to boot over a dependency it never calls.
        from app.ai.anthropic_provider import AnthropicProvider

        return AnthropicProvider(
            settings.anthropic_api_key, settings.anthropic_model, settings.anthropic_effort
        )
    if settings.xai_api_key:
        return XaiProvider(settings.xai_api_key, settings.xai_api_base, settings.xai_model)
    return NoopProvider()
