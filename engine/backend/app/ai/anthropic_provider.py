"""Second opinion from Claude, via the official Anthropic SDK."""

from __future__ import annotations

import anthropic

from app.ai.base import SecondOpinionContext, SecondOpinionProvider, SecondOpinionResult
from app.ai.briefing import SYSTEM_PROMPT, build_user_prompt


class AnthropicProvider(SecondOpinionProvider):
    name = "claude"

    def __init__(self, api_key: str, model: str, effort: str) -> None:
        # 5 minutes. The doctor is waiting on a spinner, but a request that is
        # merely slow is worth more to them than one that gets cut off.
        self._client = anthropic.AsyncAnthropic(api_key=api_key, timeout=300.0)
        self._model = model
        self._effort = effort

    async def generate(self, ctx: SecondOpinionContext) -> SecondOpinionResult:
        try:
            # Streamed and reassembled server-side rather than returned in one
            # piece: the SDK requires streaming for large max_tokens, and a
            # long non-streamed request is the thing that hits an HTTP timeout
            # between here and Railway's proxy.
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                output_config={"effort": self._effort},
                messages=[{"role": "user", "content": build_user_prompt(ctx)}],
            ) as stream:
                message = await stream.get_final_message()

            if message.stop_reason == "refusal":
                return SecondOpinionResult(
                    status="error",
                    reason="The model declined to answer this one. The engine's routing above is unaffected.",
                    model=self._model,
                )

            text = "\n".join(b.text for b in message.content if b.type == "text").strip()
            if not text:
                return SecondOpinionResult(
                    status="error", reason="The model returned an empty response.", model=self._model
                )
            return SecondOpinionResult(status="success", content=text, model=self._model)

        # Each of these fails for a different reason and needs a different fix,
        # and the message goes on screen in front of a doctor -- a raw stack
        # trace string tells them nothing they can act on.
        except anthropic.AuthenticationError:
            return SecondOpinionResult(
                status="error", reason="The AI key is missing or wrong (ANTHROPIC_API_KEY).", model=self._model
            )
        except anthropic.RateLimitError:
            return SecondOpinionResult(
                status="error", reason="Rate limited. Wait a few seconds and try again.", model=self._model
            )
        except anthropic.APITimeoutError:
            return SecondOpinionResult(
                status="error", reason="The AI took too long to answer. Try again.", model=self._model
            )
        except anthropic.APIStatusError as exc:
            return SecondOpinionResult(
                status="error", reason=f"AI service error {exc.status_code}.", model=self._model
            )
        except anthropic.APIConnectionError:
            return SecondOpinionResult(
                status="error", reason="Could not reach the AI service.", model=self._model
            )
        except Exception as exc:  # noqa: BLE001 -- any failure degrades to a banner, never a 500
            return SecondOpinionResult(status="error", reason=str(exc), model=self._model)
