import pytest

from app.engine.evaluator import evaluate_protocol
from app.engine.namespace import build_base_namespace
from app.engine.protocol_loader import load_protocols

PID = "angina_stable_v1"


@pytest.fixture(scope="module")
def protocol():
    return load_protocols()[PID]


def p(*parts: str) -> str:
    return ".".join(["protocols", PID, *parts])


def gate0_clear(**overrides):
    base = {
        p("gate0_acs_exit", "duration"): "1_to_20_min",
        p("gate0_acs_exit", "rest_pain"): False,
        p("gate0_acs_exit", "g02"): False,
        p("gate0_acs_exit", "g03"): False,
        p("gate0_acs_exit", "g04"): False,
    }
    base.update(overrides)
    return base


def run(protocol, raw_answers, shared_answers=None, tier="tertiary"):
    namespace = build_base_namespace(
        core={"primary_symptom": "chest_pain", "facility_tier": tier}, shared=shared_answers or {}
    )
    return evaluate_protocol(protocol, namespace, raw_answers, shared_answers or {})


# ---------- Gate 0 ----------

def test_gate0_fires_on_rest_pain(protocol):
    result = run(protocol, gate0_clear(**{p("gate0_acs_exit", "rest_pain"): True}))
    assert result.status == "resolved"
    assert result.terminal["code"] == "ACS_SUSPECTED"
    assert result.tracks == []  # Track A/B never ran


def test_gate0_fires_on_over_20_min_duration(protocol):
    answers = gate0_clear()
    answers[p("gate0_acs_exit", "duration")] = "over_20_min"
    result = run(protocol, answers)
    assert result.terminal["code"] == "ACS_SUSPECTED"


@pytest.mark.parametrize("field", ["g02", "g03", "g04"])
def test_gate0_fires_on_each_crescendo_field(protocol, field):
    answers = gate0_clear(**{p("gate0_acs_exit", field): True})
    result = run(protocol, answers)
    assert result.terminal["code"] == "ACS_SUSPECTED"


def test_gate0_incomplete_returns_only_gate0_frontier(protocol):
    result = run(protocol, {p("gate0_acs_exit", "duration"): "1_to_20_min"})
    assert result.status == "active"
    assert {f.field.id for f in result.frontier} == {"rest_pain", "g02", "g03", "g04"}


# ---------- Full pathway scenarios ----------

POTENTIATING_FACTORS = [
    "anaemia", "thyrotoxicosis", "pregnancy", "febrile_illness",
    "lvh", "arrhythmia", "bronchodilators_or_steroids",
]  # uncontrolled_htn and chf are shared-sourced now -- see `shared` dict below
INTERLOCK_SCREEN = [
    "asthma_or_bronchospastic_copd", "bradycardia_or_high_grade_avb", "ckd_or_hyperkalaemia",
    "pde5_inhibitor_recent", "severe_aortic_stenosis",
]


def full_context(known_cad=False, extra=None):
    answers = {p("context", "dyslipidaemia"): False, p("context", "family_history_cad"): False}
    answers.update({p("potentiating_factors", f): False for f in POTENTIATING_FACTORS})
    answers.update({p("interlock_screen", f): False for f in INTERLOCK_SCREEN})
    if extra:
        answers.update(extra)
    shared = {
        "known_cad": known_cad, "diabetes": False, "htn_dx": False, "current_smoker": False,
        "htn_uncontrolled": False, "chf": False, "ckd": False,
    }
    return answers, shared


def all_track_b_false():
    return {p("tracks", "track_b", f"B{i}_{name}"): False for i, name in enumerate(
        ["fatigue", "breathlessness", "sweating", "epigastric"], start=1
    )}


def test_typical_angina_resolves_t2(protocol):
    answers = gate0_clear()
    answers.update({
        p("tracks", "track_a", "A1_quality_site"): "diffuse_retrosternal",
        p("tracks", "track_a", "A2_provocation"): "exertion_predictable",
        p("tracks", "track_a", "A3_relief"): "rest_or_ntg_1_2min",
        p("tracks", "track_a", "A1b_radiation"): ["none"],
        p("tracks", "track_a", "A2b_post_prandial"): False,
    })
    answers.update(all_track_b_false())
    ctx, shared = full_context()
    answers.update(ctx)
    result = run(protocol, answers, shared)
    assert result.status == "resolved"
    assert result.terminal["code"] == "T2"
    track_a = next(t for t in result.tracks if t.track_id == "track_a")
    assert track_a.resolution == "typical"
    assert track_a.positive_count == 3


def test_atypical_two_of_three_resolves_t2(protocol):
    answers = gate0_clear()
    answers.update({
        p("tracks", "track_a", "A1_quality_site"): "diffuse_retrosternal",  # positive
        p("tracks", "track_a", "A2_provocation"): "rest_only",  # negative
        p("tracks", "track_a", "A3_relief"): "rest_or_ntg_1_2min",  # positive
        p("tracks", "track_a", "A1b_radiation"): ["none"],
        p("tracks", "track_a", "A2b_post_prandial"): False,
    })
    answers.update(all_track_b_false())
    ctx, shared = full_context()
    answers.update(ctx)
    result = run(protocol, answers, shared)
    assert result.terminal["code"] == "T2"
    track_a = next(t for t in result.tracks if t.track_id == "track_a")
    assert track_a.resolution == "atypical"
    assert track_a.positive_count == 2


def test_non_anginal_with_track_b_positive_resolves_t3(protocol):
    answers = gate0_clear()
    answers.update({
        p("tracks", "track_a", "A1_quality_site"): "finger_point",
        p("tracks", "track_a", "A2_provocation"): "rest_only",
        p("tracks", "track_a", "A3_relief"): "no_relief",
        p("tracks", "track_a", "A1b_radiation"): ["none"],
        p("tracks", "track_a", "A2b_post_prandial"): False,
    })
    tb = all_track_b_false()
    tb[p("tracks", "track_b", "B2_breathlessness")] = True
    answers.update(tb)
    ctx, shared = full_context()
    answers.update(ctx)
    result = run(protocol, answers, shared)
    assert result.terminal["code"] == "T3"
    track_a = next(t for t in result.tracks if t.track_id == "track_a")
    assert track_a.resolution == "non_anginal"


def test_non_anginal_track_b_negative_known_cad_resolves_t4(protocol):
    answers = gate0_clear()
    answers.update({
        p("tracks", "track_a", "A1_quality_site"): "finger_point",
        p("tracks", "track_a", "A2_provocation"): "rest_only",
        p("tracks", "track_a", "A3_relief"): "no_relief",
        p("tracks", "track_a", "A1b_radiation"): ["none"],
        p("tracks", "track_a", "A2b_post_prandial"): False,
    })
    answers.update(all_track_b_false())
    ctx, shared = full_context(known_cad=True)
    answers.update(ctx)
    result = run(protocol, answers, shared)
    assert result.terminal["code"] == "T4"


def test_non_anginal_track_b_negative_no_known_cad_resolves_t5(protocol):
    answers = gate0_clear()
    answers.update({
        p("tracks", "track_a", "A1_quality_site"): "finger_point",
        p("tracks", "track_a", "A2_provocation"): "rest_only",
        p("tracks", "track_a", "A3_relief"): "no_relief",
        p("tracks", "track_a", "A1b_radiation"): ["none"],
        p("tracks", "track_a", "A2b_post_prandial"): False,
    })
    answers.update(all_track_b_false())
    ctx, shared = full_context(known_cad=False)
    answers.update(ctx)
    result = run(protocol, answers, shared)
    assert result.terminal["code"] == "T5"


# ---------- Skip rules ----------

def test_skip_rule_1_skips_a2b_and_a3_and_forces_non_anginal(protocol):
    answers = gate0_clear()
    answers.update({
        p("tracks", "track_a", "A1_quality_site"): "above_jaw",
        p("tracks", "track_a", "A2_provocation"): "neck_arm_or_respiration",
        p("tracks", "track_a", "A1b_radiation"): ["none"],
        # A2b and A3 deliberately NOT answered -- should be skipped by rule
    })
    answers.update(all_track_b_false())
    ctx, shared = full_context()
    answers.update(ctx)
    result = run(protocol, answers, shared)
    assert result.status == "resolved", "protocol should resolve without A2b/A3 ever being asked"
    track_a = next(t for t in result.tracks if t.track_id == "track_a")
    assert track_a.resolution == "non_anginal"
    assert track_a.per_field["A2b_post_prandial"]["status"] == "skipped"
    assert track_a.per_field["A3_relief"]["status"] == "skipped"
    skipped_ids = {u["field_id"] for u in result.unassessed}
    assert {"A2b_post_prandial", "A3_relief"} <= skipped_ids


def test_skip_rule_2_skips_only_a3_via_derived_n1(protocol):
    answers = gate0_clear(**{p("gate0_acs_exit", "duration"): "under_1_min"})
    answers.update({
        p("tracks", "track_a", "A1_quality_site"): "diffuse_retrosternal",  # positive, to prove cap still applies
        p("tracks", "track_a", "A2_provocation"): "no_trigger",  # negative
        p("tracks", "track_a", "A1b_radiation"): ["none"],
        p("tracks", "track_a", "A2b_post_prandial"): False,  # not skipped by this rule, must be answered
        # A3 deliberately NOT answered -- should be skipped via N1 + no_trigger
    })
    answers.update(all_track_b_false())
    ctx, shared = full_context()
    answers.update(ctx)
    result = run(protocol, answers, shared)
    track_a = next(t for t in result.tracks if t.track_id == "track_a")
    assert track_a.per_field["A3_relief"]["status"] == "skipped"
    assert track_a.positive_count == 1  # only A1; A2 negative, A3 excluded
    assert track_a.resolution == "non_anginal", "capped even though A1 was positive"


def test_a3_not_tried_resolves_unknown_not_negative_and_does_not_downgrade(protocol):
    answers = gate0_clear()
    answers.update({
        p("tracks", "track_a", "A1_quality_site"): "diffuse_retrosternal",  # positive
        p("tracks", "track_a", "A2_provocation"): "exertion_predictable",  # positive
        p("tracks", "track_a", "A3_relief"): "not_tried",
        p("tracks", "track_a", "A1b_radiation"): ["none"],
        p("tracks", "track_a", "A2b_post_prandial"): False,
    })
    answers.update(all_track_b_false())
    ctx, shared = full_context()
    answers.update(ctx)
    result = run(protocol, answers, shared)
    track_a = next(t for t in result.tracks if t.track_id == "track_a")
    assert track_a.per_field["A3_relief"]["status"] == "unknown"
    assert track_a.unknown_count == 1
    assert track_a.positive_count == 2
    assert track_a.resolution == "atypical", "2 positive axes -> atypical, unknown must not downgrade further"


# ---------- Shared context field gating ----------

def test_context_shared_field_blocks_until_answered_in_shared_store(protocol):
    answers = gate0_clear()
    answers.update({
        p("tracks", "track_a", "A1_quality_site"): "finger_point",
        p("tracks", "track_a", "A2_provocation"): "rest_only",
        p("tracks", "track_a", "A3_relief"): "no_relief",
        p("tracks", "track_a", "A1b_radiation"): ["none"],
        p("tracks", "track_a", "A2b_post_prandial"): False,
        p("context", "dyslipidaemia"): False,
        p("context", "family_history_cad"): False,
    })
    answers.update(all_track_b_false())
    # shared answers deliberately empty -> known_cad/diabetes/etc unanswered
    result = run(protocol, answers, shared_answers={})
    assert result.status == "active"
    frontier_paths = {f.answer_path for f in result.frontier}
    assert "shared.known_cad" in frontier_paths


# ---------- Potentiating factors + drug proposals ----------

def typical_t2_answers():
    answers = gate0_clear()
    answers.update({
        p("tracks", "track_a", "A1_quality_site"): "diffuse_retrosternal",
        p("tracks", "track_a", "A2_provocation"): "exertion_predictable",
        p("tracks", "track_a", "A3_relief"): "rest_or_ntg_1_2min",
        p("tracks", "track_a", "A1b_radiation"): ["none"],
        p("tracks", "track_a", "A2b_post_prandial"): False,
    })
    answers.update(all_track_b_false())
    ctx, shared = full_context()
    answers.update(ctx)
    return answers, shared


def find_drug(result, entry_id):
    block = next(b for b in result.drug_blocks if b["id"] == "step2_drugs")
    return next(e for e in block["entries"] if e["id"] == entry_id)


def test_t2_full_regimen_includes_anti_ischemic_and_quarantines_ticagrelor(protocol):
    answers, shared = typical_t2_answers()
    result = run(protocol, answers, shared)
    assert result.status == "resolved"
    assert result.terminal["code"] == "T2"
    block = next(b for b in result.drug_blocks if b["id"] == "step2_drugs")
    entry_ids = {e["id"] for e in block["entries"]}
    assert "metoprolol" in entry_ids  # anti-ischemic group present for T2
    assert find_drug(result, "aspirin")["state"] == "clear"
    assert find_drug(result, "ticagrelor")["state"] == "quarantined"


def test_asthma_blocks_metoprolol_with_reason(protocol):
    answers, shared = typical_t2_answers()
    answers[p("interlock_screen", "asthma_or_bronchospastic_copd")] = True
    result = run(protocol, answers, shared)
    metoprolol = find_drug(result, "metoprolol")
    assert metoprolol["state"] == "block"
    assert "bronchospasm" in metoprolol["block_reasons"][0]["reason"].lower()
    assert metoprolol["block_reasons"][0]["vitalis_addition"] is True
    # aspirin is unaffected by an interlock that doesn't apply to it
    assert find_drug(result, "aspirin")["state"] == "clear"


def test_pregnancy_asked_once_blocks_ace_inhibitors(protocol):
    answers, shared = typical_t2_answers()
    answers[p("potentiating_factors", "pregnancy")] = True
    result = run(protocol, answers, shared)
    assert find_drug(result, "ramipril")["state"] == "block"
    assert find_drug(result, "enalapril")["state"] == "block"


def test_t4_secondary_prevention_only_no_anti_ischemic(protocol):
    answers = gate0_clear()
    answers.update({
        p("tracks", "track_a", "A1_quality_site"): "finger_point",
        p("tracks", "track_a", "A2_provocation"): "rest_only",
        p("tracks", "track_a", "A3_relief"): "no_relief",
        p("tracks", "track_a", "A1b_radiation"): ["none"],
        p("tracks", "track_a", "A2b_post_prandial"): False,
    })
    answers.update(all_track_b_false())
    ctx, shared = full_context(known_cad=True)
    answers.update(ctx)
    result = run(protocol, answers, shared)
    assert result.terminal["code"] == "T4"
    block = next(b for b in result.drug_blocks if b["id"] == "step2_drugs")
    entry_ids = {e["id"] for e in block["entries"]}
    assert "aspirin" in entry_ids
    assert "metoprolol" not in entry_ids  # anti-ischemic gated out for T4
    assert "trimetazidine" not in entry_ids


def test_t5_no_angina_medication_at_all(protocol):
    answers = gate0_clear()
    answers.update({
        p("tracks", "track_a", "A1_quality_site"): "finger_point",
        p("tracks", "track_a", "A2_provocation"): "rest_only",
        p("tracks", "track_a", "A3_relief"): "no_relief",
        p("tracks", "track_a", "A1b_radiation"): ["none"],
        p("tracks", "track_a", "A2b_post_prandial"): False,
    })
    answers.update(all_track_b_false())
    ctx, shared = full_context(known_cad=False)
    answers.update(ctx)
    result = run(protocol, answers, shared)
    assert result.terminal["code"] == "T5"
    block = next(b for b in result.drug_blocks if b["id"] == "step2_drugs")
    assert block["entries"] == []


def test_tertiary_only_drugs_hidden_below_tertiary_tier(protocol):
    answers, shared = typical_t2_answers()
    result_phc = run(protocol, answers, shared, tier="phc")
    block_phc = next(b for b in result_phc.drug_blocks if b["id"] == "step2_drugs")
    assert "trimetazidine" not in {e["id"] for e in block_phc["entries"]}
    assert block_phc["hidden_count"] == 3  # trimetazidine, nicorandil, ranolazine

    result_tertiary = run(protocol, answers, shared, tier="tertiary")
    block_tertiary = next(b for b in result_tertiary.drug_blocks if b["id"] == "step2_drugs")
    assert "trimetazidine" in {e["id"] for e in block_tertiary["entries"]}


def test_potentiating_factors_surfaced_in_context_blocks(protocol):
    answers, shared = typical_t2_answers()
    answers[p("potentiating_factors", "anaemia")] = True
    result = run(protocol, answers, shared)
    pf_block = next(b for b in result.context_blocks if b["id"] == "potentiating_factors")
    assert pf_block["render_hint"] == "flag_positive"
    assert pf_block["fields"]["anaemia"] is True
