import pytest

from app.engine.evaluator import evaluate_protocol
from app.engine.namespace import build_base_namespace
from app.engine.protocol_loader import load_protocols

PID = "af_placeholder_v1"


@pytest.fixture(scope="module")
def protocol():
    return load_protocols()[PID]


def p(*parts: str) -> str:
    return ".".join(["protocols", PID, *parts])


def base_core(hr=90):
    return {"ecg": {"rhythm": "af"}, "vitals": {"hr": hr}}


def run(protocol, raw_answers, shared_answers=None, core=None):
    namespace = build_base_namespace(core=core or base_core(), shared=shared_answers or {})
    return evaluate_protocol(protocol, namespace, raw_answers, shared_answers or {})


def test_gate_a_not_confirmed_terminates(protocol):
    result = run(protocol, {p("gate_a_confirmation", "af_confirmed"): False})
    assert result.status == "resolved"
    assert result.terminal["code"] == "AF_NOT_CONFIRMED"


def test_gate_b_instability_terminates(protocol):
    result = run(
        protocol,
        {
            p("gate_a_confirmation", "af_confirmed"): True,
            p("gate_b_instability", "hemodynamic_instability"): True,
        },
    )
    assert result.status == "resolved"
    assert result.terminal["code"] == "AF_INSTABILITY_EMERGENCY"


def test_gate_b_bleed_terminates(protocol):
    result = run(
        protocol,
        {
            p("gate_a_confirmation", "af_confirmed"): True,
            p("gate_b_instability", "hemodynamic_instability"): False,
            p("gate_b_bleed", "major_bleed_on_oac"): True,
        },
    )
    assert result.status == "resolved"
    assert result.terminal["code"] == "AF_MAJOR_BLEED_EMERGENCY"


def _clear_gates():
    return {
        p("gate_a_confirmation", "af_confirmed"): True,
        p("gate_b_instability", "hemodynamic_instability"): False,
        p("gate_b_bleed", "major_bleed_on_oac"): False,
    }


def test_full_resolution_with_checklist_and_thresholds_and_single_choice(protocol):
    answers = _clear_gates()
    answers.update(
        {
            p("categorize", "duration_category"): "persistent",
            p("categorize", "rate_control_only"): False,
            p("tracks", "t1_anticoagulation", "age_75_or_older"): True,
            p("tracks", "t2_bleeding_risk", "prior_major_bleed"): False,
            p("tracks", "t2_bleeding_risk", "labile_inr_or_interacting_factors"): False,
            p("tracks", "t4_rhythm_control_substrate", "substrate"): "cad_or_lvh",
        }
    )
    shared = {
        "htn_dx": True, "htn_uncontrolled": True, "diabetes": False, "chf": False,
        "stroke": False, "tia_only": False, "vascular_disease": False, "ckd": False, "hepatic": False,
        "echo_status": "no_significant_lesion",
    }
    result = run(protocol, answers, shared, core=base_core(hr=130))

    assert result.status == "resolved"
    assert result.terminal["code"] == "AF_TRACKS_ASSESSED"

    t1a = next(t for t in result.tracks if t.track_id == "t1a_valve_assessment")
    assert t1a.resolution == "doac_eligible"

    t1 = next(t for t in result.tracks if t.track_id == "t1_anticoagulation")
    assert t1.resolution == "2 of 7 factors present"  # age_75_or_older + shared htn_dx

    t2 = next(t for t in result.tracks if t.track_id == "t2_bleeding_risk")
    assert t2.resolution == "1 of 5 factors present"  # htn_uncontrolled only

    t3 = next(t for t in result.tracks if t.track_id == "t3_rate_control")
    assert t3.resolution == "Rate control indicated — heart rate over 110"

    t4 = next(t for t in result.tracks if t.track_id == "t4_rhythm_control_substrate")
    assert t4.resolution == "cad_or_lvh"


def test_rate_control_thresholds_bradycardia_emergency(protocol):
    answers = _clear_gates()
    answers.update(
        {
            p("categorize", "duration_category"): "paroxysmal",
            p("categorize", "rate_control_only"): False,
            p("tracks", "t1_anticoagulation", "age_75_or_older"): False,
            p("tracks", "t2_bleeding_risk", "hypertension_uncontrolled"): False,
            p("tracks", "t2_bleeding_risk", "renal_or_hepatic_impairment"): False,
            p("tracks", "t2_bleeding_risk", "prior_major_bleed"): False,
            p("tracks", "t2_bleeding_risk", "labile_inr_or_interacting_factors"): False,
            p("tracks", "t4_rhythm_control_substrate", "substrate"): "normal_heart",
        }
    )
    shared = {"htn_dx": False, "diabetes": False, "chf": False, "stroke": False, "tia_only": False, "vascular_disease": False}
    result = run(protocol, answers, shared, core=base_core(hr=42))
    t3 = next(t for t in result.tracks if t.track_id == "t3_rate_control")
    assert t3.resolution == "Emergency — heart rate under 50"


def test_af_auto_activation_trigger_present_in_protocol_definition(protocol):
    assert protocol.activation.auto_trigger is not None
    assert protocol.fidelity == "reduced_fidelity_placeholder"


def test_t4_substrate_prefill_hint_from_angina_track_a(protocol):
    answers = _clear_gates()
    answers.update(
        {
            p("categorize", "duration_category"): "paroxysmal",
            p("categorize", "rate_control_only"): False,
            p("tracks", "t1_anticoagulation", "age_75_or_older"): False,
            p("tracks", "t2_bleeding_risk", "hypertension_uncontrolled"): False,
            p("tracks", "t2_bleeding_risk", "renal_or_hepatic_impairment"): False,
            p("tracks", "t2_bleeding_risk", "prior_major_bleed"): False,
            p("tracks", "t2_bleeding_risk", "labile_inr_or_interacting_factors"): False,
            # substrate deliberately unanswered -- should surface in frontier with a suggested_value
        }
    )
    shared = {"htn_dx": False, "diabetes": False, "chf": False, "stroke": False, "tia_only": False, "vascular_disease": False}
    namespace = build_base_namespace(core=base_core(hr=90), shared=shared)
    namespace["protocols"]["angina_stable_v1"] = {"tracks": {"track_a": {"resolution": "typical"}}}
    result = evaluate_protocol(protocol, namespace, answers, shared)
    assert result.status == "active"
    substrate_field = next(f for f in result.frontier if f.field.id == "substrate")
    assert substrate_field.suggested_value == "cad_or_lvh"
