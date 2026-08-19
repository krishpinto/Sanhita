import pytest

from app.engine.evaluator import evaluate_protocol
from app.engine.namespace import build_base_namespace
from app.engine.protocol_loader import load_protocols

PID = "rhd_v1"


@pytest.fixture(scope="module")
def protocol():
    return load_protocols()[PID]


def p(*parts: str) -> str:
    return ".".join(["protocols", PID, *parts])


JONES_FIELDS = [
    "carditis", "arthritis", "chorea", "subcutaneous_nodules", "erythema_marginatum",
    "monoarthralgia", "fever_ge_38", "esr_ge_30_or_crp_ge_3", "prolonged_pr_interval", "recurrent_episode",
]


def jones_answers(**overrides):
    answers = {p("presentation_router", "presentation"): "acute_rheumatic_fever_suspected"}
    for f in JONES_FIELDS:
        answers[p("tracks", "jones_criteria", f)] = overrides.get(f, False)
    return answers


def run(protocol, raw_answers, shared_answers=None, tier="district"):
    namespace = build_base_namespace(
        core={"primary_symptom": "suspected_acute_rheumatic_fever", "facility_tier": tier},
        shared=shared_answers or {},
    )
    return evaluate_protocol(protocol, namespace, raw_answers, shared_answers or {})


def jones_resolution(result):
    return next(t for t in result.tracks if t.track_id == "jones_criteria").resolution


# ---------- Jones criteria patterns ----------

def test_chorea_alone_meets_criteria_without_strep_evidence(protocol):
    answers = jones_answers(chorea=True)
    result = run(protocol, answers)
    assert jones_resolution(result) == "met_chorea_alone"
    # strep_evidence should be skipped -- chorea alone needs no streptococcal evidence
    strep_field = next(
        (f for f in result.frontier if f.field.id == "streptococcal_evidence"), None
    )
    assert strep_field is None  # not in frontier -- it was skipped, not pending


def test_two_major_meets_criteria(protocol):
    answers = jones_answers(carditis=True, arthritis=True)
    result = run(protocol, answers)
    assert jones_resolution(result) == "met_two_major"


def test_one_major_two_minor_meets_criteria(protocol):
    answers = jones_answers(carditis=True, fever_ge_38=True, esr_ge_30_or_crp_ge_3=True)
    result = run(protocol, answers)
    assert jones_resolution(result) == "met_one_major_two_minor"


def test_recurrent_plus_three_minor_meets_criteria(protocol):
    answers = jones_answers(
        recurrent_episode=True, fever_ge_38=True, esr_ge_30_or_crp_ge_3=True, prolonged_pr_interval=True
    )
    result = run(protocol, answers)
    assert jones_resolution(result) == "met_recurrent_three_minor"


def test_one_major_one_minor_does_not_meet_criteria(protocol):
    answers = jones_answers(carditis=True, fever_ge_38=True)
    result = run(protocol, answers)
    assert jones_resolution(result) == "not_met"


def test_criteria_met_without_strep_evidence_flags_not_blocks(protocol):
    answers = jones_answers(carditis=True, arthritis=True)
    answers[p("strep_evidence", "streptococcal_evidence")] = False
    result = run(protocol, answers)
    flag = next(d for d in result.derived_tags if d["id"] == "strep_evidence_flag")
    assert flag["value"] is True
    # acute treatment still proceeds -- flagged, not blocked
    acute = next(b for b in result.drug_blocks if b["id"] == "acute_treatment")
    assert acute["status"] == "ready"
    assert all(e["state"] != "block" for e in acute["entries"])


def test_established_valve_disease_skips_jones_entirely(protocol):
    answers = {p("presentation_router", "presentation"): "established_valve_disease"}
    result = run(protocol, answers, shared_answers={"echo_status": "no_significant_lesion"})
    assert jones_resolution(result) == "not_applicable_established_valve_disease"
    jones_frontier = [f for f in result.frontier if f.track_id == "jones_criteria"]
    assert jones_frontier == []
    acute = next(b for b in result.drug_blocks if b["id"] == "acute_treatment")
    assert acute["status"] == "not_applicable"
    assert acute["entries"] == []


# ---------- Valve -> anticoagulant decision table ----------

def full_jones_not_met():
    return jones_answers()  # everything false -> not_met


def test_valve_echo_not_performed_blocks(protocol):
    answers = full_jones_not_met()
    result = run(protocol, answers, shared_answers={"echo_status": "not_performed"})
    valve = next(t for t in result.tracks if t.track_id == "valve_anticoagulant")
    assert valve.resolution == "blocked_echo_not_performed"


def test_valve_no_significant_lesion_is_doac_eligible(protocol):
    answers = full_jones_not_met()
    result = run(protocol, answers, shared_answers={"echo_status": "no_significant_lesion"})
    valve = next(t for t in result.tracks if t.track_id == "valve_anticoagulant")
    assert valve.resolution == "doac_eligible"


def test_valve_ms_not_graded_blocks(protocol):
    answers = full_jones_not_met()
    result = run(
        protocol, answers,
        shared_answers={"echo_status": "lesions_present", "mitral_stenosis_severity": "not_graded"},
    )
    valve = next(t for t in result.tracks if t.track_id == "valve_anticoagulant")
    assert valve.resolution == "blocked_ms_not_graded"


def test_valve_moderate_severe_ms_hard_blocks_doac(protocol):
    answers = full_jones_not_met()
    result = run(
        protocol, answers,
        shared_answers={"echo_status": "lesions_present", "mitral_stenosis_severity": "moderate_or_severe"},
    )
    valve = next(t for t in result.tracks if t.track_id == "valve_anticoagulant")
    assert valve.resolution == "vka_hard_block_doac"


def test_valve_mechanical_prosthesis_hard_blocks_doac(protocol):
    answers = full_jones_not_met()
    answers[p("tracks", "valve_anticoagulant", "aortic_stenosis_severe")] = False
    result = run(
        protocol, answers,
        shared_answers={
            "echo_status": "lesions_present",
            "mitral_stenosis_severity": "mild",
            "prosthetic_valve": "mechanical",
        },
    )
    valve = next(t for t in result.tracks if t.track_id == "valve_anticoagulant")
    assert valve.resolution == "vka_hard_block_doac"


def test_valve_bioprosthetic_mild_ms_is_doac_eligible(protocol):
    answers = full_jones_not_met()
    answers[p("tracks", "valve_anticoagulant", "aortic_stenosis_severe")] = False
    result = run(
        protocol, answers,
        shared_answers={
            "echo_status": "lesions_present",
            "mitral_stenosis_severity": "absent",
            "prosthetic_valve": "bioprosthetic",
        },
    )
    valve = next(t for t in result.tracks if t.track_id == "valve_anticoagulant")
    assert valve.resolution == "doac_eligible"


def test_prosthetic_valve_question_skipped_when_ms_moderate_severe(protocol):
    # per the diagram: MS moderate/severe routes straight to VKA, prosthetic check never asked
    answers = full_jones_not_met()
    result = run(
        protocol, answers,
        shared_answers={"echo_status": "lesions_present", "mitral_stenosis_severity": "moderate_or_severe"},
    )
    prosthetic_in_frontier = any(f.field.id == "prosthetic_valve" for f in result.frontier)
    assert prosthetic_in_frontier is False


# ---------- Aetiology + secondary prophylaxis + duration ----------

def test_rheumatic_aetiology_triggers_prophylaxis_and_duration(protocol):
    answers = full_jones_not_met()
    answers[p("tracks", "valve_anticoagulant", "aortic_stenosis_severe")] = False
    answers[p("tracks", "valve_aetiology", "aetiology")] = "rheumatic"
    answers[p("tracks", "duration", "had_carditis")] = False
    answers[p("tracks", "duration", "residual_valve_disease")] = False
    result = run(
        protocol, answers,
        shared_answers={
            "echo_status": "lesions_present", "mitral_stenosis_severity": "absent", "prosthetic_valve": "none",
        },
    )
    prophylaxis = next(b for b in result.drug_blocks if b["id"] == "secondary_prophylaxis")
    assert prophylaxis["status"] == "ready"
    assert len(prophylaxis["entries"]) == 2
    duration = next(t for t in result.tracks if t.track_id == "duration")
    assert duration.resolution == "5 years, or until age 21, whichever is longer"


def test_carditis_no_residual_disease_duration(protocol):
    answers = full_jones_not_met()
    answers[p("tracks", "valve_anticoagulant", "aortic_stenosis_severe")] = False
    answers[p("tracks", "valve_aetiology", "aetiology")] = "rheumatic"
    answers[p("tracks", "duration", "had_carditis")] = True
    answers[p("tracks", "duration", "residual_valve_disease")] = False
    result = run(
        protocol, answers,
        shared_answers={
            "echo_status": "lesions_present", "mitral_stenosis_severity": "absent", "prosthetic_valve": "none",
        },
    )
    duration = next(t for t in result.tracks if t.track_id == "duration")
    assert duration.resolution == "10 years, or until age 21"


def test_persistent_valve_disease_duration_overrides_carditis(protocol):
    answers = full_jones_not_met()
    answers[p("tracks", "valve_anticoagulant", "aortic_stenosis_severe")] = False
    answers[p("tracks", "valve_aetiology", "aetiology")] = "rheumatic"
    answers[p("tracks", "duration", "had_carditis")] = False
    answers[p("tracks", "duration", "residual_valve_disease")] = True
    result = run(
        protocol, answers,
        shared_answers={
            "echo_status": "lesions_present", "mitral_stenosis_severity": "absent", "prosthetic_valve": "none",
        },
    )
    duration = next(t for t in result.tracks if t.track_id == "duration")
    assert duration.resolution == "10 years, or until age 40 — often lifelong if severe"


def test_degenerative_aetiology_no_prophylaxis(protocol):
    answers = full_jones_not_met()
    answers[p("tracks", "valve_anticoagulant", "aortic_stenosis_severe")] = False
    answers[p("tracks", "valve_aetiology", "aetiology")] = "degenerative_or_unclear"
    result = run(
        protocol, answers,
        shared_answers={
            "echo_status": "lesions_present", "mitral_stenosis_severity": "absent", "prosthetic_valve": "none",
        },
    )
    prophylaxis = next(b for b in result.drug_blocks if b["id"] == "secondary_prophylaxis")
    assert prophylaxis["status"] == "not_applicable"
    assert prophylaxis["entries"] == []


def test_referral_flag_on_severe_aortic_stenosis(protocol):
    answers = full_jones_not_met()
    answers[p("tracks", "valve_anticoagulant", "aortic_stenosis_severe")] = True
    answers[p("tracks", "valve_aetiology", "aetiology")] = "degenerative_or_unclear"
    result = run(
        protocol, answers,
        shared_answers={
            "echo_status": "lesions_present", "mitral_stenosis_severity": "absent", "prosthetic_valve": "none",
        },
    )
    flag = next(d for d in result.derived_tags if d["id"] == "referral_indicated")
    assert flag["value"] is True


def test_full_acute_episode_end_to_end_resolves(protocol):
    answers = jones_answers(carditis=True, arthritis=True)
    answers[p("strep_evidence", "streptococcal_evidence")] = True
    answers[p("tracks", "valve_anticoagulant", "aortic_stenosis_severe")] = False
    answers[p("tracks", "valve_aetiology", "aetiology")] = "rheumatic"
    answers[p("tracks", "duration", "had_carditis")] = True
    answers[p("tracks", "duration", "residual_valve_disease")] = False
    result = run(
        protocol, answers,
        shared_answers={
            "echo_status": "lesions_present", "mitral_stenosis_severity": "mild", "prosthetic_valve": "none",
        },
    )
    assert result.status == "resolved"
    assert result.terminal["code"] == "RHD_ACUTE_EPISODE"
