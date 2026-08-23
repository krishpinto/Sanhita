"""Second opinion from Google Gemini.

Raw REST over httpx rather than the google-genai SDK, deliberately. The
request is one POST with a system instruction and one user turn -- an SDK
buys nothing at that size, and it costs a dependency whose version surface
moves faster than this file will.
"""

from __future__ import annotations

import httpx

from app.ai.base import SecondOpinionContext, SecondOpinionProvider, SecondOpinionResult
from app.ai.briefing import SYSTEM_PROMPT, build_user_prompt

# Gemini can decline to answer clinical content outright. The API's default
# thresholds are tuned for consumer chat, not for a tool a physician is using
# on purpose, so they are relaxed here to the least restrictive setting the
# API offers. It can still block -- that path is handled below and shown to
# the doctor as a failed request, never as an empty opinion.
_SAFETY_SETTINGS = [
    {"category": category, "threshold": "BLOCK_NONE"}
    for category in (
        "HARM_CATEGORY_HARASSMENT",
        "HARM_CATEGORY_HATE_SPEECH",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "HARM_CATEGORY_DANGEROUS_CONTENT",
    )
]


class GeminiProvider(SecondOpinionProvider):
    """Same briefing as every other provider -- see app/ai/briefing.py."""

    name = "gemini"

    def __init__(self, api_key: str, api_base: str, model: str) -> None:
        self._api_key = api_key
        self._api_base = api_base.rstrip("/")
        self._model = model

    async def generate(self, ctx: SecondOpinionContext) -> SecondOpinionResult:
        url = f"{self._api_base}/models/{self._model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": build_user_prompt(ctx)}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4000},
            "safetySettings": _SAFETY_SETTINGS,
        }
        try:
            # Generous, because a thinking model reading a full encounter is
            # not a 20-second job, and a request cut off at the client looks
            # to the doctor like a broken feature rather than a slow one.
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    url,
                    # The key goes in a header, never in the query string --
                    # URLs end up in proxy logs and browser history.
                    headers={"x-goog-api-key": self._api_key},
                    json=payload,
                )

            failure = self._http_failure(response)
            if failure:
                return failure
            return self._read(response.json())

        except httpx.TimeoutException:
            return self._error("The AI took too long to answer. Try again.")
        except httpx.HTTPError:
            return self._error("Could not reach the AI service.")
        except Exception as exc:  # noqa: BLE001 -- any failure degrades to a banner, never a 500
            return self._error(str(exc))

    def _error(self, reason: str) -> SecondOpinionResult:
        return SecondOpinionResult(status="error", reason=reason, model=self._model)

    def _http_failure(self, response: httpx.Response) -> SecondOpinionResult | None:
        """Each of these needs a different fix, and the message goes on screen
        in front of a doctor -- a raw stack trace tells them nothing they can
        act on."""
        if response.is_success:
            return None
        if response.status_code in (401, 403):
            return self._error("The AI key is missing, wrong, or not enabled (GEMINI_API_KEY).")
        if response.status_code == 404:
            return self._error(f"The AI model '{self._model}' was not found on this key.")
        if response.status_code == 429:
            return self._error("Free-tier limit reached. Wait a minute and try again.")
        if response.status_code >= 500:
            return self._error("The AI service is having trouble. Try again shortly.")
        return self._error(f"AI service error {response.status_code}.")

    def _read(self, data: dict) -> SecondOpinionResult:
        blocked = (data.get("promptFeedback") or {}).get("blockReason")
        if blocked:
            return self._error(f"The AI declined to read this encounter ({blocked}).")

        candidates = data.get("candidates") or []
        if not candidates:
            return self._error("The AI returned nothing.")

        candidate = candidates[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        # A thinking model returns its reasoning as parts flagged `thought`.
        # Those are working-out, not the opinion, and must not reach the
        # doctor as though they were.
        text = "\n".join(p["text"] for p in parts if p.get("text") and not p.get("thought")).strip()

        if not text:
            reason = candidate.get("finishReason")
            if reason == "MAX_TOKENS":
                return self._error("The AI ran out of room before it answered. Try again.")
            if reason == "SAFETY":
                return self._error("The AI declined to answer this one.")
            return self._error(f"The AI returned an empty response ({reason or 'no reason given'}).")

        return SecondOpinionResult(status="success", content=text, model=self._model)
