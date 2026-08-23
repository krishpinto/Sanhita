from __future__ import annotations

import httpx

from app.ai.base import SecondOpinionContext, SecondOpinionProvider, SecondOpinionResult
from app.ai.briefing import SYSTEM_PROMPT, build_user_prompt

class XaiProvider(SecondOpinionProvider):
    """Same briefing as every other provider -- see app/ai/briefing.py."""

    name = "xai"

    def __init__(self, api_key: str, api_base: str, model: str) -> None:
        self._api_key = api_key
        self._api_base = api_base.rstrip("/")
        self._model = model

    async def generate(self, ctx: SecondOpinionContext) -> SecondOpinionResult:
        try:
            # Generous, because a reasoning model on a full encounter is not a
            # 20-second job and a truncated request looks to the doctor like a
            # broken feature rather than a slow one.
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{self._api_base}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": self._model,
                        "max_tokens": 4000,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": build_user_prompt(ctx)},
                        ],
                    },
                )
                if response.status_code == 401:
                    return SecondOpinionResult(
                        status="error", reason="The AI key is missing or wrong (XAI_API_KEY).", model=self._model
                    )
                if response.status_code == 429:
                    return SecondOpinionResult(
                        status="error", reason="Rate limited. Wait a few seconds and try again.", model=self._model
                    )
                response.raise_for_status()
                content = (response.json()["choices"][0]["message"]["content"] or "").strip()
                if not content:
                    return SecondOpinionResult(
                        status="error", reason="The model returned an empty response.", model=self._model
                    )
                return SecondOpinionResult(status="success", content=content, model=self._model)
        except httpx.TimeoutException:
            return SecondOpinionResult(
                status="error", reason="The AI took too long to answer. Try again.", model=self._model
            )
        except Exception as exc:  # noqa: BLE001 -- any failure degrades to a banner, never a 500
            return SecondOpinionResult(status="error", reason=str(exc), model=self._model)
