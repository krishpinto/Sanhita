"""The consultation history list, and the lock on it.

Every other endpoint is scoped to one encounter by its bearer token. This one
crosses encounters, so most of these tests are about who is refused rather
than about what is returned.
"""

import pytest

from app.config import settings

from tests.test_api_flow import _answer, _complete_prelude, _new_encounter, client

KEY = "test-review-key"
AUTH = {"Authorization": f"Bearer {KEY}"}


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(settings, "admin_key", KEY)


# --- the lock --------------------------------------------------------------


def test_the_page_is_disabled_not_open_when_no_key_is_configured(monkeypatch):
    """The failure mode of the opposite default is every patient record
    readable by anyone who guesses the path."""
    monkeypatch.setattr(settings, "admin_key", None)
    assert client.get("/consultations").status_code == 503
    assert client.get("/consultations", headers=AUTH).status_code == 503


def test_no_key_is_refused(enabled):
    assert client.get("/consultations").status_code == 401


def test_a_wrong_key_is_refused(enabled):
    resp = client.get("/consultations", headers={"Authorization": "Bearer not-the-key"})
    assert resp.status_code == 401


def test_an_encounter_token_does_not_open_the_history(enabled):
    """A doctor's own encounter token must not become a key to everyone
    else's records."""
    _, headers = _new_encounter()
    assert client.get("/consultations", headers=headers).status_code == 401


def test_the_review_key_does_not_open_a_single_encounter(enabled):
    """And the reverse: the shared key is not a master token for the
    per-encounter endpoints."""
    eid, _ = _new_encounter()
    assert client.get(f"/encounters/{eid}/next-step", headers=AUTH).status_code == 401


def test_the_right_key_is_accepted(enabled):
    assert client.get("/consultations", headers=AUTH).status_code == 200


# --- what it lists ---------------------------------------------------------


def _row_for(eid, headers=AUTH):
    body = client.get("/consultations", headers=headers).json()
    matches = [c for c in body["consultations"] if c["id"] == eid]
    assert matches, f"{eid} is not in the history"
    return matches[0]


def test_a_new_encounter_shows_up(enabled):
    eid, headers = _new_encounter()
    _complete_prelude(eid, headers, "History Patient", 47, "F", ["chest_pain"])
    row = _row_for(eid)
    assert row["patient_name"] == "History Patient"
    assert row["patient_age"] == 47
    assert row["patient_sex"] == "F"
    assert row["symptoms"] == ["chest_pain"]
    assert row["facility_tier"] == "district"
    assert row["questions_answered"] > 0


def test_newest_first(enabled):
    first, h1 = _new_encounter()
    _complete_prelude(first, h1, "Older", 50, "M", ["chest_pain"])
    second, h2 = _new_encounter()
    _complete_prelude(second, h2, "Newer", 51, "M", ["chest_pain"])

    ids = [c["id"] for c in client.get("/consultations", headers=AUTH).json()["consultations"]]
    assert ids.index(second) < ids.index(first)


def test_a_safety_exit_reads_as_an_outcome_not_as_unfinished(enabled):
    """An encounter that stopped at ST elevation reached the most important
    outcome the tool has. It must not look abandoned in the list."""
    eid, headers = _new_encounter()
    _complete_prelude(eid, headers, "STEMI History", 70, "F", ["chest_pain"])
    _answer(
        eid,
        headers,
        "core.ecg",
        {"availability": "performed_reviewed", "st_elevation": True, "rhythm": "normal_sinus"},
    )
    row = _row_for(eid)
    assert row["safety_exit"]
    assert "ST" in row["safety_exit"] or "STEMI" in row["safety_exit"].upper()


def test_the_row_carries_a_token_that_opens_that_consultation(enabled):
    """The whole point of the page: click a past patient and read the record
    back, exactly as the doctor saw it."""
    eid, headers = _new_encounter()
    _complete_prelude(eid, headers, "Reopen Me", 47, "F", ["chest_pain"])

    row = _row_for(eid)
    reopened = client.get(
        f"/encounters/{eid}/next-step", headers={"Authorization": f"Bearer {row['access_token']}"}
    )
    assert reopened.status_code == 200


def test_paging_reports_the_true_total(enabled):
    for _ in range(3):
        eid, headers = _new_encounter()
        _complete_prelude(eid, headers, "Paged", 40, "M", ["chest_pain"])

    body = client.get("/consultations", headers=AUTH, params={"limit": 2}).json()
    assert len(body["consultations"]) == 2
    assert body["total"] >= 3
    assert body["limit"] == 2

    second_page = client.get("/consultations", headers=AUTH, params={"limit": 2, "offset": 2}).json()
    first_ids = {c["id"] for c in body["consultations"]}
    assert not first_ids & {c["id"] for c in second_page["consultations"]}


def test_the_list_does_not_cost_an_engine_walk_per_row(enabled):
    """Outcomes come from the stored activations. If someone re-points this
    at compute_next_step, the page starts getting slower with every
    consultation ever recorded -- catch it here rather than in production."""
    import app.engine_service as engine_service

    calls = {"n": 0}
    real = engine_service.compute_next_step

    def counting(*args, **kwargs):
        calls["n"] += 1
        return real(*args, **kwargs)

    engine_service.compute_next_step = counting
    try:
        assert client.get("/consultations", headers=AUTH).status_code == 200
    finally:
        engine_service.compute_next_step = real
    assert calls["n"] == 0
