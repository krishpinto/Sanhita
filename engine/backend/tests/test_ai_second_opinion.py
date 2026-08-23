"""The AI second opinion: what it is told, and what it does when the call fails.

The briefing tests matter more than they look. The engine's whole reason for
having a second reader is to catch what its rules structurally cannot see --
age fit being the standing example. A model that is never told the age, or is
told "8 findings recorded" instead of which eight, cannot catch anything. So
these assert on the presence of specific facts in the prompt, not on shape.
"""

import json

import httpx
import pytest
from sqlmodel import Session, select

from app.ai.base import SecondOpinionContext
from app.ai.briefing import SYSTEM_PROMPT, build_user_prompt
from app.ai.gemini_provider import GeminiProvider
from app.ai.noop_provider import NoopProvider
from app.answer_log import transcript
from app.db import engine
from app.engine_service import compute_next_step, serialize_protocol_result
from app.models_db import Encounter
from app.result_payload import core_summary, differential_audit, unrun_protocols

from tests.test_api_flow import _answer, _complete_prelude, _new_encounter, client


def _resolved_encounter(age=58, symptoms=("chest_pain",)):
    """One complete encounter, walked to a real routing result."""
    eid, headers = _new_encounter()
    _complete_prelude(eid, headers, "Briefing Test", age, "M", list(symptoms))
    for _ in range(400):
        step = client.get(f"/encounters/{eid}/next-step", headers=headers).json()
        if step.get("core_terminal") or step["ready_for_result"]:
            break
        if step["core_frontier"]:
            field = step["core_frontier"][0]
        elif step["offered_protocols"]:
            pid = step["offered_protocols"][0]["protocol_id"]
            client.post(f"/encounters/{eid}/activate-protocol/{pid}", headers=headers)
            continue
        else:
            pending = [p for p in step["active_protocols"] if p["frontier"]]
            if not pending:
                break
            field = pending[0]["frontier"][0]
        _answer(eid, headers, field["answer_path"], _value_for(field["field"]))
    return eid, headers


def _value_for(field):
    kind, fid = field["field_type"], field["id"]
    if fid == "duration":
        return "1_to_20_min"
    if kind == "structured_ecg":
        return {"availability": "performed_reviewed", "rhythm": "normal_sinus", "rate": 78}
    if kind == "structured_vitals":
        return {"hr": 78, "bp_systolic": 146, "bp_diastolic": 92, "spo2": 98}
    if kind == "findings_review":
        return {"exertional_relieved_by_rest": True}
    if kind == "boolean":
        return False
    if kind == "single_select":
        return field["options"][0]["value"]
    if kind in ("multi_select", "differential_review"):
        return []
    if kind == "number":
        return 0
    return ""


def _briefing_for(eid) -> str:
    """The exact text a provider would send, built the way the endpoint builds
    it. If these two ever drift, every assertion below is testing fiction."""
    with Session(engine) as session:
        encounter = session.exec(select(Encounter).where(Encounter.id == eid)).one()
        step = compute_next_step(session, encounter)
        ctx = SecondOpinionContext(
            core=core_summary(encounter),
            protocols=[serialize_protocol_result(r) for r in step.active_protocols],
            differential=differential_audit(encounter),
            unrun_protocols=unrun_protocols(step),
            answer_log=transcript(session, encounter.id),
            core_terminal=step.core_terminal,
        )
    return build_user_prompt(ctx)


def _result(eid, headers) -> dict:
    resp = client.get(f"/encounters/{eid}/result", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- what the model is told ------------------------------------------------


def test_the_briefing_carries_the_patients_age_and_facility():
    eid, _ = _resolved_encounter(age=21)
    text = _briefing_for(eid)
    assert "21-year-old" in text
    assert "district" in text


def test_the_system_prompt_tells_the_model_the_engine_ignores_age():
    # The one blind spot we know about by name. If this instruction is ever
    # dropped, the second reader stops being able to catch the thing the
    # doctor actually caught in testing.
    assert "does not weigh age" in SYSTEM_PROMPT


def test_the_briefing_carries_every_question_and_answer_not_a_count():
    eid, headers = _resolved_encounter()
    text = _briefing_for(eid)
    log = _result(eid, headers)["answer_log"]
    questions = [entry["question"] for event in log for entry in event["entries"]]
    assert len(questions) > 20
    for question in questions:
        assert question in text, f"the model was never shown: {question}"


def test_the_briefing_says_not_assessed_rather_than_leaving_it_out():
    # Silence would read to the model as a negative finding, which is the one
    # thing the safety model forbids everywhere else in this codebase.
    eid, _ = _resolved_encounter()
    text = _briefing_for(eid)
    assert "did NOT assess" in text
    assert "unknown, NOT negative" in text


def test_the_briefing_carries_the_differential_reasons_not_just_the_verdicts():
    eid, headers = _resolved_encounter()
    text = _briefing_for(eid)
    items = _result(eid, headers)["differential"]["items"]
    assert items
    for item in items:
        assert item["label"] in text
        assert item["status"] in text


def test_the_briefing_carries_the_routing_the_engine_chose():
    eid, headers = _resolved_encounter()
    text = _briefing_for(eid)
    protocols = _result(eid, headers)["protocols"]
    assert protocols
    for protocol in protocols:
        assert protocol["protocol_name"] in text
        assert protocol["terminal"]["headline"] in text


def test_a_correction_reaches_the_model_as_a_correction():
    eid, headers = _resolved_encounter(age=58)
    _answer(eid, headers, "core.age", 61)
    assert "[changed from an earlier answer]" in _briefing_for(eid)


def test_every_provider_is_briefed_identically():
    """Two providers briefed differently would make "the AI disagreed" mean
    different things depending on which key happened to be set that week."""
    from app.ai import briefing, gemini_provider, xai_provider

    assert gemini_provider.SYSTEM_PROMPT is briefing.SYSTEM_PROMPT
    assert xai_provider.SYSTEM_PROMPT is briefing.SYSTEM_PROMPT
    assert gemini_provider.build_user_prompt is xai_provider.build_user_prompt


# --- what happens when the call fails --------------------------------------


def _provider() -> GeminiProvider:
    return GeminiProvider("secret-key-value", "https://example.invalid/v1beta", "gemini-3.7-flash")


def test_a_thinking_models_reasoning_never_reaches_the_doctor():
    result = _provider()._read(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "let me work through this", "thought": True},
                            {"text": "VERDICT\nAGREE"},
                        ]
                    },
                    "finishReason": "STOP",
                }
            ]
        }
    )
    assert result.status == "success"
    assert result.content == "VERDICT\nAGREE"


def test_a_blocked_prompt_is_an_error_not_an_empty_opinion():
    result = _provider()._read({"promptFeedback": {"blockReason": "SAFETY"}})
    assert result.status == "error"
    assert result.content is None
    assert "declined" in result.reason


def test_running_out_of_room_says_so_rather_than_returning_nothing():
    result = _provider()._read({"candidates": [{"content": {"parts": []}, "finishReason": "MAX_TOKENS"}]})
    assert result.status == "error"
    assert "ran out of room" in result.reason


@pytest.mark.parametrize(
    "status_code,expected",
    [
        (401, "key is missing"),
        (403, "key is missing"),
        (404, "was not found"),
        (429, "Free-tier limit"),
        (500, "having trouble"),
    ],
)
def test_each_failure_says_what_to_do_about_it(status_code, expected):
    """A doctor reading "Client error 401 Unauthorized for url ..." learns
    nothing. Every failure here names the thing that is actually wrong."""
    response = httpx.Response(status_code, request=httpx.Request("POST", "https://example.invalid"))
    result = _provider()._http_failure(response)
    assert result is not None
    assert result.status == "error"
    assert expected in result.reason


def test_the_api_key_never_appears_in_the_request_url():
    """Keys in query strings end up in proxy logs and browser history."""
    provider = _provider()
    url = f"{provider._api_base}/models/{provider._model}:generateContent"
    assert "secret-key-value" not in url


# --- provider selection ----------------------------------------------------


def test_no_key_is_a_supported_state_not_an_error():
    assert NoopProvider().name == "none"


def test_the_factory_prefers_gemini_when_more_than_one_key_is_set(monkeypatch):
    from app.ai import factory
    from app.config import settings

    monkeypatch.setattr(settings, "gemini_api_key", "g")
    monkeypatch.setattr(settings, "xai_api_key", "x")
    factory.get_ai_provider.cache_clear()
    try:
        assert factory.get_ai_provider().name == "gemini"
    finally:
        factory.get_ai_provider.cache_clear()


def test_the_factory_falls_back_to_xai_when_only_that_key_is_set(monkeypatch):
    from app.ai import factory
    from app.config import settings

    monkeypatch.setattr(settings, "gemini_api_key", None)
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.setattr(settings, "xai_api_key", "x")
    factory.get_ai_provider.cache_clear()
    try:
        assert factory.get_ai_provider().name == "xai"
    finally:
        factory.get_ai_provider.cache_clear()


# --- the request that actually goes out ------------------------------------

_REPLY = "VERDICT\nAGREE WITH CAVEATS -- age fit is poor."


def test_the_outgoing_request_is_shaped_the_way_gemini_expects(monkeypatch):
    """Everything above this test exercises our own parsing. This one checks
    the half that talks to Google: get the URL, the auth header or the body
    key names wrong and every other test still passes while the feature is
    dead in production."""
    import asyncio

    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": _REPLY}]}, "finishReason": "STOP"}]},
        )

    real_client = httpx.AsyncClient

    def fake_client(*args, **kwargs):
        return real_client(*args, transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", fake_client)

    provider = GeminiProvider("secret-key-value", "https://gemini.test/v1beta", "gemini-3.7-flash")
    ctx = SecondOpinionContext(core={"age": 21, "sex": "M", "symptoms": ["chest_pain"]}, protocols=[])
    result = asyncio.run(provider.generate(ctx))

    assert result.status == "success"
    assert result.content == _REPLY
    assert result.model == "gemini-3.7-flash"

    assert seen["url"] == "https://gemini.test/v1beta/models/gemini-3.7-flash:generateContent"
    assert "secret-key-value" not in seen["url"]
    assert seen["headers"]["x-goog-api-key"] == "secret-key-value"

    body = seen["body"]
    assert body["systemInstruction"]["parts"][0]["text"] == SYSTEM_PROMPT
    assert body["contents"][0]["role"] == "user"
    assert "21-year-old M" in body["contents"][0]["parts"][0]["text"]
    assert body["generationConfig"]["maxOutputTokens"] == 4000
    # Consumer-chat safety thresholds will refuse a chest-pain workup.
    assert {s["threshold"] for s in body["safetySettings"]} == {"BLOCK_NONE"}
