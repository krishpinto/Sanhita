from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
client.__enter__()  # trigger FastAPI lifespan/startup (init_db) once for the whole test module

RISK_FACTOR_IDS = [
    "htn_dx", "htn_uncontrolled", "known_cad", "prior_mi", "stroke", "tia_only",
    "ckd", "hepatic", "diabetes", "current_smoker", "chf", "vascular_disease", "obesity",
]


def _new_encounter() -> tuple[str, dict]:
    resp = client.post("/encounters")
    assert resp.status_code == 200
    body = resp.json()
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    eid = body["encounter_id"]
    _answer(eid, headers, "core.facility_tier", "district")
    return eid, headers


def _answer(eid, headers, field_path, value):
    resp = client.post(f"/encounters/{eid}/answer", json={"field_path": field_path, "value": value}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _complete_prelude(eid, headers, name, age, sex, symptoms, risk_factors=None):
    """Walks facility_tier (already done by _new_encounter) -> patient details
    -> shared risk factors -> symptoms -> differential review (auto-clears,
    excluding nothing) -- returns the next-step payload right after, so the
    caller can continue with ECG/vitals."""
    _answer(eid, headers, "core.name", name)
    _answer(eid, headers, "core.age", age)
    _answer(eid, headers, "core.sex", sex)

    overrides = risk_factors or {}
    step = None
    for fid in RISK_FACTOR_IDS:
        step = _answer(eid, headers, f"shared.{fid}", overrides.get(fid, False))

    step = _answer(eid, headers, "core.symptoms", symptoms)

    # the findings screen only appears if the symptom set raised something --
    # answering nothing (empty dict) leaves every item "not yet assessed",
    # which still counts as surviving (unknown != negative).
    if step["core_frontier"] and step["core_frontier"][0]["field"]["field_type"] == "findings_review":
        step = _answer(eid, headers, "core.differential_answers", {})

    return step


def test_full_angina_encounter_resolves_t2_via_http():
    eid, headers = _new_encounter()

    step = client.get(f"/encounters/{eid}/next-step", headers=headers).json()
    assert {f["field"]["id"] for f in step["core_frontier"]} == {"name", "age", "sex"}

    step = _complete_prelude(eid, headers, "Test Patient", 58, "M", ["chest_pain"])
    assert step["core_frontier"][0]["field"]["id"] == "ecg"

    ecg = {
        "availability": "performed_reviewed",
        "rhythm": "normal_sinus",
        "q_waves": False,
        "st_t_changes": False,
        "st_elevation": False,
        "bbb": False,
        "chamber_enlargement": False,
        "pre_excitation": False,
        "qt_interval": "normal",
    }
    step = _answer(eid, headers, "core.ecg", ecg)
    assert step["core_frontier"][0]["field"]["id"] == "vitals"

    step = _answer(eid, headers, "core.vitals", None)  # explicit skip, vitals optional
    assert step["core_frontier"] == []
    # chest_pain alone raises stable_angina (and AF, RHD) in the differential --
    # surviving_modules includes angina_stable_v1, which is what offers it here.
    assert any(o["protocol_id"] == "angina_stable_v1" for o in step["offered_protocols"])

    step = client.post(f"/encounters/{eid}/activate-protocol/angina_stable_v1", headers=headers).json()
    assert len(step["active_protocols"]) == 1
    angina = step["active_protocols"][0]
    frontier_ids = {f["field"]["id"] for f in angina["frontier"]}
    assert frontier_ids == {"duration", "rest_pain", "g02", "g03", "g04"}

    pid = "angina_stable_v1"
    _answer(eid, headers, f"protocols.{pid}.gate0_acs_exit.duration", "1_to_20_min")
    _answer(eid, headers, f"protocols.{pid}.gate0_acs_exit.rest_pain", False)
    _answer(eid, headers, f"protocols.{pid}.gate0_acs_exit.g02", False)
    _answer(eid, headers, f"protocols.{pid}.gate0_acs_exit.g03", False)
    step = _answer(eid, headers, f"protocols.{pid}.gate0_acs_exit.g04", False)

    angina = step["active_protocols"][0]
    assert angina["status"] == "active"
    frontier_paths = {f["answer_path"] for f in angina["frontier"]}
    assert f"protocols.{pid}.tracks.track_a.A1_quality_site" in frontier_paths
    assert f"protocols.{pid}.tracks.track_b.B1_fatigue" in frontier_paths

    _answer(eid, headers, f"protocols.{pid}.tracks.track_a.A1_quality_site", "diffuse_retrosternal")
    _answer(eid, headers, f"protocols.{pid}.tracks.track_a.A2_provocation", "exertion_predictable")
    _answer(eid, headers, f"protocols.{pid}.tracks.track_a.A3_relief", "rest_or_ntg_1_2min")
    _answer(eid, headers, f"protocols.{pid}.tracks.track_a.A1b_radiation", ["none"])
    _answer(eid, headers, f"protocols.{pid}.tracks.track_a.A2b_post_prandial", False)
    _answer(eid, headers, f"protocols.{pid}.tracks.track_b.B1_fatigue", False)
    _answer(eid, headers, f"protocols.{pid}.tracks.track_b.B2_breathlessness", False)
    _answer(eid, headers, f"protocols.{pid}.tracks.track_b.B3_sweating", False)
    step = _answer(eid, headers, f"protocols.{pid}.tracks.track_b.B4_epigastric", False)

    angina = step["active_protocols"][0]
    frontier_paths = {f["answer_path"] for f in angina["frontier"]}
    assert f"protocols.{pid}.context.dyslipidaemia" in frontier_paths  # risk factors already resolved shared.*

    resp = client.get(f"/encounters/{eid}/result", headers=headers)
    assert resp.status_code == 409  # not ready yet -- context still outstanding

    step = _answer(eid, headers, f"protocols.{pid}.context.dyslipidaemia", False)
    step = _answer(eid, headers, f"protocols.{pid}.context.family_history_cad", False)

    # Terminal is already known even though potentiating factors / interlocks
    # (post-terminal blocks) are still outstanding -- protocol stays "active".
    angina = step["active_protocols"][0]
    assert angina["status"] == "active"
    assert angina["terminal"]["code"] == "T2"

    for factor in [
        "anaemia", "thyrotoxicosis", "pregnancy", "febrile_illness",
        "lvh", "arrhythmia", "bronchodilators_or_steroids",
    ]:
        _answer(eid, headers, f"protocols.{pid}.potentiating_factors.{factor}", False)
    for factor in [
        "asthma_or_bronchospastic_copd", "bradycardia_or_high_grade_avb", "ckd_or_hyperkalaemia",
        "pde5_inhibitor_recent",
    ]:
        _answer(eid, headers, f"protocols.{pid}.interlock_screen.{factor}", False)
    step = _answer(eid, headers, f"protocols.{pid}.interlock_screen.severe_aortic_stenosis", False)

    assert step["ready_for_result"] is True
    angina = step["active_protocols"][0]
    assert angina["status"] == "resolved"
    assert angina["terminal"]["code"] == "T2"
    drug_block = next(b for b in angina["drug_blocks"] if b["id"] == "step2_drugs")
    aspirin = next(e for e in drug_block["entries"] if e["id"] == "aspirin")
    assert aspirin["state"] == "clear"

    result = client.get(f"/encounters/{eid}/result", headers=headers)
    assert result.status_code == 200
    payload = result.json()
    assert payload["protocols"][0]["terminal"]["code"] == "T2"

    # Exercises SecondOpinionContext construction for real (not just the
    # early 409) -- this is the path that broke when primary_symptom was
    # replaced by the symptoms list and this call site wasn't updated.
    ai_resp = client.post(f"/encounters/{eid}/ai-opinion", headers=headers)
    assert ai_resp.status_code == 200
    ai_body = ai_resp.json()
    assert ai_body["provider"] == "none"
    assert ai_body["status"] == "unavailable"
    assert ai_body["reason"] == "AI_NOT_CONFIGURED"
    assert payload["ai_opinion"] is None
    assert payload["doctor_opinion"] is None
    assert "differential" in payload


def test_st_elevation_hard_exit_before_any_protocol():
    eid, headers = _new_encounter()
    step = _complete_prelude(eid, headers, "STEMI Test", 70, "F", ["chest_pain"])
    assert step["core_frontier"][0]["field"]["id"] == "ecg"
    step = _answer(
        eid,
        headers,
        "core.ecg",
        {"availability": "performed_reviewed", "st_elevation": True, "rhythm": "normal_sinus"},
    )
    assert step["core_terminal"]["code"] == "ST_ELEVATION_SUSPECTED_STEMI"

    result = client.get(f"/encounters/{eid}/result", headers=headers)
    assert result.status_code == 200
    assert result.json()["core_terminal"]["code"] == "ST_ELEVATION_SUSPECTED_STEMI"


def test_doctor_opinion_and_noop_ai_opinion():
    eid, headers = _new_encounter()
    resp = client.post(
        f"/encounters/{eid}/doctor-opinion",
        json={"doctor_note": "I disagree, suspect musculoskeletal pain.", "structured_alternate_diagnosis": None},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = client.post(f"/encounters/{eid}/ai-opinion", headers=headers)
    assert resp.status_code == 409  # no protocol resolved yet


def test_unauthorized_without_token():
    resp = client.get("/encounters/does-not-matter/next-step")
    assert resp.status_code == 401


def test_encounter_summary_endpoint_reflects_symptoms_not_stale_primary_symptom():
    eid, headers = _new_encounter()
    _complete_prelude(eid, headers, "Summary Test", 44, "M", ["chest_pain", "diaphoresis"])
    resp = client.get(f"/encounters/{eid}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["patient_name"] == "Summary Test"
    assert set(body["symptoms"]) == {"chest_pain", "diaphoresis"}
    assert body["facility_tier"] == "district"


def test_af_auto_activates_on_ecg_rhythm_regardless_of_symptoms():
    eid, headers = _new_encounter()
    # symptom set is chest pain only -- nothing palpitations-like -- AF should
    # still auto-activate purely from the ECG rhythm finding, per the source's
    # "asymmetric override" rule: the tracing can overrule the differential.
    step = _complete_prelude(eid, headers, "AF Test", 66, "F", ["chest_pain"])
    assert step["core_frontier"][0]["field"]["id"] == "ecg"
    _answer(
        eid,
        headers,
        "core.ecg",
        {"availability": "performed_reviewed", "rhythm": "af", "st_elevation": False},
    )
    step = _answer(eid, headers, "core.vitals", {"hr": 130})

    active_ids = {p["protocol_id"] for p in step["active_protocols"]}
    assert "af_placeholder_v1" in active_ids
    # Angina is only offered (chest_pain survived the differential too), never forced
    assert any(o["protocol_id"] == "angina_stable_v1" for o in step["offered_protocols"])

    af = next(p for p in step["active_protocols"] if p["protocol_id"] == "af_placeholder_v1")
    assert af["fidelity"] == "reduced_fidelity_placeholder"
    assert af["status"] == "active"
    assert af["frontier"][0]["field"]["id"] == "af_confirmed"


def test_diabetic_exertional_breathlessness_without_chest_pain_still_offers_angina():
    """The case the v0.4 rewrite exists for: a diabetic with ONLY exertional
    breathlessness (no chest pain) must still get Angina offered -- the old
    single-select primary_symptom router would have missed this patient."""
    eid, headers = _new_encounter()
    step = _complete_prelude(
        eid, headers, "Diabetic Patient", 61, "F",
        ["exertional_breathlessness_or_fatigue"],
        risk_factors={"diabetes": True},
    )
    assert step["core_frontier"][0]["field"]["id"] == "ecg"
    ecg = {"availability": "performed_reviewed", "rhythm": "normal_sinus", "st_elevation": False}
    step = _answer(eid, headers, "core.ecg", ecg)
    step = _answer(eid, headers, "core.vitals", None)

    assert any(o["protocol_id"] == "angina_stable_v1" for o in step["offered_protocols"])
    assert any(o["protocol_id"] == "rhd_v1" for o in step["offered_protocols"])
    assert not any(o["protocol_id"] == "af_placeholder_v1" for o in step["offered_protocols"])


def test_differential_exclusion_withdraws_module_offer():
    """Answering an item's discriminator question 'No' rules it out of the
    differential -- ruled-out items are recorded as 'considered and ruled
    out' with a reason, not silently dropped, but they do stop driving
    module activation."""
    eid, headers = _new_encounter()
    _answer(eid, headers, "core.name", "Excl Test")
    _answer(eid, headers, "core.age", 50)
    _answer(eid, headers, "core.sex", "M")
    for fid in RISK_FACTOR_IDS:
        _answer(eid, headers, f"shared.{fid}", False)
    step = _answer(eid, headers, "core.symptoms", ["palpitations"])
    field = step["core_frontier"][0]["field"]
    assert field["field_type"] == "findings_review"

    # The doctor answers findings, not diagnoses. Recording "no irregular
    # pulse" and "no murmur" is what withdraws the AF and RHD modules --
    # nobody was asked to rule out a protocol.
    answers = {"irregular_pulse": False, "murmur": False}
    assert {f["id"] for f in field["findings"]} >= set(answers)
    step = _answer(eid, headers, "core.differential_answers", answers)
    ecg = {"availability": "performed_reviewed", "rhythm": "normal_sinus", "st_elevation": False}
    step = _answer(eid, headers, "core.ecg", ecg)
    step = _answer(eid, headers, "core.vitals", None)

    assert step["offered_protocols"] == []
    assert step["active_protocols"] == []
