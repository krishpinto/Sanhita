"""Changing an answer already given, and the record of having changed it.

Correcting an answer used to be refused outright (409, "already answered"),
so the only way to fix a mis-tap was to start the patient over. Every test
here pins one half of the fix: the correction itself, what a correction is
allowed to invalidate, and the fact that the encounter's record keeps both
versions rather than quietly replacing one with the other.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
client.__enter__()  # trigger FastAPI lifespan/startup (init_db) once for the module

RISK_FACTOR_IDS = [
    "htn_dx", "htn_uncontrolled", "known_cad", "prior_mi", "stroke", "tia_only",
    "ckd", "hepatic", "diabetes", "current_smoker", "chf", "vascular_disease", "obesity",
]

ANGINA_FINDINGS = {
    "pulses_equal": True, "pleuritic_pain": False, "constitutional": False,
    "chest_wall_reproducible": False, "murmur": False, "irregular_pulse": False,
    "reflux_pattern": False, "exertional_relieved_by_rest": True,
}


def _answer(eid, headers, field_path, value, expect=200):
    resp = client.post(
        f"/encounters/{eid}/answer", json={"field_path": field_path, "value": value}, headers=headers
    )
    assert resp.status_code == expect, resp.text
    return resp.json() if resp.status_code == 200 else resp


def _prelude(symptoms=("chest_pain", "exertional_breathlessness_or_fatigue"), findings=None):
    body = client.post("/encounters").json()
    eid = body["encounter_id"]
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    _answer(eid, headers, "core.facility_tier", "district")
    _answer(eid, headers, "core.name", "Test Patient")
    _answer(eid, headers, "core.age", 58)
    _answer(eid, headers, "core.sex", "M")
    for fid in RISK_FACTOR_IDS:
        _answer(eid, headers, f"shared.{fid}", False)
    _answer(eid, headers, "core.symptoms", list(symptoms))
    step = _answer(eid, headers, "core.differential_answers", findings or dict(ANGINA_FINDINGS))
    return eid, headers, step


def _drive_to_end(eid, headers, step, overrides=None):
    """Answer whatever is outstanding until nothing is, starting any protocol
    that gets offered."""
    overrides = overrides or {}

    def pick(f):
        fid, ftype = f["id"], f["field_type"]
        if fid in overrides:
            return overrides[fid]
        if ftype == "structured_ecg":
            return {"availability": "performed_reviewed", "rhythm": "normal_sinus", "rate": 78}
        if ftype == "structured_vitals":
            return None
        if fid == "differential_confirmations":
            return []
        if ftype == "boolean":
            return False
        if ftype == "single_select":
            return f["options"][0]["value"]
        if ftype == "multi_select":
            return []
        if ftype == "number":
            return 0
        return ""

    for _ in range(300):
        if step["core_terminal"]:
            return step
        if step["core_frontier"]:
            ff = step["core_frontier"][0]
            step = _answer(eid, headers, ff["answer_path"], pick(ff["field"]))
            continue
        if step["offered_protocols"]:
            pid = step["offered_protocols"][0]["protocol_id"]
            step = client.post(f"/encounters/{eid}/activate-protocol/{pid}", headers=headers).json()
            continue
        pending = [p for p in step["active_protocols"] if p["frontier"]]
        if pending:
            ff = pending[0]["frontier"][0]
            step = _answer(eid, headers, ff["answer_path"], pick(ff["field"]))
            continue
        return step
    raise AssertionError("did not settle")


# --------------------------------------------------------------- the basics


def test_an_answered_field_can_be_answered_again():
    eid, headers, _ = _prelude()
    _answer(eid, headers, "core.age", 21)
    assert client.get(f"/encounters/{eid}", headers=headers).json()["patient_age"] == 21


def test_a_path_that_was_never_answerable_is_still_refused():
    """Allowing corrections must not turn the answer endpoint into a
    write-anything endpoint. Only paths this encounter actually holds are
    open to being changed."""
    eid, headers, _ = _prelude()
    _answer(eid, headers, "protocols.rhd_v1.no_such_block.no_such_field", True, expect=409)


def test_answered_fields_come_back_alongside_the_frontier():
    """A reloaded client has to be able to find its way back into everything
    already recorded, so the engine reports what is settled, not only what is
    outstanding."""
    eid, headers, step = _prelude()
    paths = {a["answer_path"] for a in step["core_answered"]}
    assert "core.age" in paths
    assert "core.symptoms" in paths
    assert "shared.diabetes" in paths
    assert "core.differential_answers" in paths


# ------------------------------------------------- what a correction undoes


def test_changing_the_symptoms_re_asks_the_findings():
    """The findings screen only exists because of the symptom set -- which
    questions appear, and what each one settles, are derived from it. Keeping
    the old answers would silently apply observations made about one
    differential to a different one."""
    eid, headers, _ = _prelude()
    step = _answer(eid, headers, "core.symptoms", ["palpitations", "irregular_pulse"])
    assert [f["field"]["id"] for f in step["core_frontier"]] == ["differential_answers"]


def test_changing_the_findings_re_asks_the_tier_one_confirmations():
    """Rule 2 in reverse: the deliberate tap that drops a killer was made
    against a particular set of findings. Change the findings and that
    decision has to be made again, not inherited."""
    eid, headers, step = _prelude()
    step = _drive_to_end(eid, headers, step)
    corrected = dict(ANGINA_FINDINGS, pulses_equal=False)
    step = _answer(eid, headers, "core.differential_answers", corrected)
    outstanding = [f["field"]["id"] for f in step["core_frontier"]]
    assert "differential_confirmations" in outstanding


def test_correcting_the_ecg_lifts_a_hard_exit():
    """The ST-elevation exit is a conclusion drawn from an answer. Tick it by
    mistake and the encounter must be recoverable -- otherwise the safest
    behaviour in the system is also the one that destroys the consultation."""
    eid, headers, step = _prelude()
    step = _drive_to_end(
        eid, headers, step,
        overrides={"ecg": {"availability": "performed_reviewed", "rhythm": "normal_sinus",
                           "st_elevation": True}},
    )
    assert step["core_terminal"]["code"] == "ST_ELEVATION_SUSPECTED_STEMI"

    step = _answer(eid, headers, "core.ecg",
                   {"availability": "performed_reviewed", "rhythm": "normal_sinus", "rate": 78})
    assert step["core_terminal"] is None
    assert client.get(f"/encounters/{eid}", headers=headers).json()["core_terminal_code"] is None


def test_correcting_a_gate_answer_withdraws_the_modules_resolution():
    eid, headers, step = _prelude()
    step = _drive_to_end(eid, headers, step, overrides={"duration": "over_20_min"})
    assert [p["terminal"]["code"] for p in step["active_protocols"]] == ["ACS_SUSPECTED"]

    step = _answer(eid, headers, "protocols.angina_stable_v1.gate0_acs_exit.duration", "1_to_20_min")
    assert [p["status"] for p in step["active_protocols"]] == ["active"]


def test_a_correction_closes_a_module_that_is_no_longer_indicated():
    """A module left running on grounds that no longer hold would keep issuing
    recommendations the differential no longer supports."""
    eid, headers, step = _prelude()
    step = _drive_to_end(eid, headers, step)
    assert [p["protocol_id"] for p in step["active_protocols"]] == ["angina_stable_v1"]

    step = _answer(eid, headers, "core.symptoms", ["palpitations", "irregular_pulse"])
    assert step["active_protocols"] == []


def test_answers_that_are_still_valid_survive_a_correction():
    """Correcting one finding must not cost the clinician everything they
    entered after it."""
    eid, headers, step = _prelude()
    step = _drive_to_end(eid, headers, step)
    before = {a["answer_path"] for a in step["active_protocols"][0]["answered"]}
    assert before

    step = _answer(eid, headers, "core.differential_answers",
                   dict(ANGINA_FINDINGS, pulses_equal=False))
    step = _drive_to_end(eid, headers, step)
    after = {a["answer_path"] for a in step["active_protocols"][0]["answered"]}
    assert before <= after


# ------------------------------------------------------------ the record


def test_the_answer_log_holds_every_question_and_answer():
    eid, headers, step = _prelude()
    _drive_to_end(eid, headers, step)
    log = client.get(f"/encounters/{eid}/result", headers=headers).json()["answer_log"]

    rows = [row for entry in log for row in entry["entries"]]
    questions = {row["question"] for row in rows}
    assert "Age" in questions
    # The findings screen is nine observations behind one answer path, and
    # each one has to appear in the record on its own.
    assert "Are the peripheral pulses equal in both arms?" in questions
    assert {"Yes", "No"} & {row["answer"] for row in rows}


def test_not_assessed_is_recorded_as_itself_never_as_no():
    """The whole safety model rests on 'we did not check' never being allowed
    to read back as 'we checked and it was fine'."""
    partial = {k: v for k, v in ANGINA_FINDINGS.items() if k != "pleuritic_pain"}
    eid, headers, step = _prelude(findings=partial)
    _drive_to_end(eid, headers, step)
    log = client.get(f"/encounters/{eid}/result", headers=headers).json()["answer_log"]

    answers = {row["question"]: row["answer"] for entry in log for row in entry["entries"]}
    assert answers["Is the pain worse on breathing in?"] == "Not assessed"


def test_a_correction_is_recorded_as_a_change_not_a_replacement():
    eid, headers, step = _prelude()
    _answer(eid, headers, "core.age", 21)
    _drive_to_end(eid, headers, step)
    log = client.get(f"/encounters/{eid}/result", headers=headers).json()["answer_log"]

    changes = [e for e in log if e["is_correction"]]
    assert len(changes) == 1
    assert changes[0]["entries"] == [{"question": "Age", "answer": "21"}]
    assert changes[0]["previous_entries"] == [{"question": "Age", "answer": "58"}]

    # and the original answer is still there, in its own place in the order
    ages = [row["answer"] for e in log for row in e["entries"] if row["question"] == "Age"]
    assert ages == ["58", "21"]
