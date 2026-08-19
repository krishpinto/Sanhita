from __future__ import annotations

import httpx

from app.ai.base import SecondOpinionContext, SecondOpinionProvider, SecondOpinionResult

_SYSTEM_PROMPT = (
    "You are a non-authoritative second opinion inside a physician-facing clinical "
    "decision-support tool called Vitalis. You will be given a structured summary of a "
    "patient encounter and the routing/output already produced by the tool's rule engine. "
    "Write a short (3-6 sentence) plain-language summary and, if you disagree with the "
    "engine's routing or think something is missing, say so plainly and explain why. "
    "You are a suggestion for the treating physician to weigh, not an instruction. "
    "Never state a definitive diagnosis -- speak in terms of likelihood and what you'd "
    "want to confirm. Do not repeat this disclaimer in your answer; the interface shows "
    "it separately."
)


def _build_user_prompt(ctx: SecondOpinionContext) -> str:
    symptoms = ctx.core.get("symptoms") or []
    lines = [f"Patient: {ctx.core.get('age')}{ctx.core.get('sex') or ''}, symptoms: {', '.join(symptoms) or 'none recorded'}"]
    for p in ctx.protocols:
        lines.append(f"\n--- {p['protocol_name']} ({p['status']}) ---")
        if p.get("fidelity") == "reduced_fidelity_placeholder":
            lines.append(f"[reduced-fidelity module: {p.get('fidelity_note')}]")
        if p.get("terminal"):
            lines.append(f"Routing: {p['terminal']['headline']}")
        for t in p.get("tracks", []):
            lines.append(f"{t['label']}: {t['resolution']} ({t['positive_count']} positive of {t['total_scored_fields']})")
        if p.get("unassessed"):
            lines.append("Not assessed: " + ", ".join(u["label"] for u in p["unassessed"]))
    return "\n".join(lines)


class XaiProvider(SecondOpinionProvider):
    name = "xai"

    def __init__(self, api_key: str, api_base: str, model: str) -> None:
        self._api_key = api_key
        self._api_base = api_base.rstrip("/")
        self._model = model

    async def generate(self, ctx: SecondOpinionContext) -> SecondOpinionResult:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self._api_base}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": self._model,
                        "messages": [
                            {"role": "system", "content": _SYSTEM_PROMPT},
                            {"role": "user", "content": _build_user_prompt(ctx)},
                        ],
                    },
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return SecondOpinionResult(status="success", content=content)
        except Exception as exc:  # noqa: BLE001 -- any failure degrades gracefully, never a 500
            return SecondOpinionResult(status="error", reason=str(exc))
