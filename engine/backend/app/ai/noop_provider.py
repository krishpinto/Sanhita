from app.ai.base import SecondOpinionContext, SecondOpinionProvider, SecondOpinionResult


class NoopProvider(SecondOpinionProvider):
    """Default provider when no AI API key is configured. The absence of AI
    is a normal state -- this always returns 200-equivalent status, never an
    error, so the rest of the app never has to special-case 'AI missing'."""

    name = "none"

    async def generate(self, ctx: SecondOpinionContext) -> SecondOpinionResult:
        return SecondOpinionResult(status="unavailable", reason="AI_NOT_CONFIGURED")
