"""Layer 1 (the narrowing layer) tested against the four rules it exists to
enforce -- private/context/READ-THIS-FIRST.md section 4.

These are the rules where being wrong kills the patient, so each one gets a
test that fails loudly rather than a comment asserting it is handled.

The doctor answers FINDINGS, not possibilities: one observation can settle
several items at once, and the polarity of "supports this item" is per-item
(equal pulses argue AGAINST dissection). Both properties are load-bearing and
tested below.
"""

from __future__ import annotations

import pytest

from app.differential_engine import (
    EXCLUDED,
    FINDINGS_BY_ID,
    ITEMS_BY_ID,
    PENDING_CONFIRMATION,
    PROMOTED,
    RAISED,
    build_confirmation_field,
    build_findings_field,
    carried_findings,
    compute_differential,
    findings_for,
    items_by_finding,
    pending_confirmation_ids,
    raised_item_ids,
)

CHEST_PAIN = ["chest_pain"]

# The five killers. Four are policed by the exclusion engine; ACS is deliberately
# not one of them -- it is owned formally by the angina module's Gate 0.
KILLERS_NEEDING_CONFIRMATION = {
    "aortic_dissection",
    "pulmonary_embolism",
    "pneumothorax",
    "severe_aortic_stenosis",
}

# A completely reassuring examination, expressed as findings rather than as
# conclusions. Note pulses_equal=True is the NORMAL answer and the one that
# argues against dissection -- polarity is not uniform, which is the point.
NORMAL_EXAM = {
    "pulses_equal": True,
    "pleuritic_pain": False,
    "constitutional": False,
    "chest_wall_reproducible": False,
    "exertional_relieved_by_rest": True,
    "murmur": False,
    "irregular_pulse": False,
    "pallor": False,
    "reflux_pattern": False,
}


def _by_id(result):
    return {i.id: i for i in result.items}


# --------------------------------------------------------------------------
# Rule 1 -- never let "we didn't check" look like "we checked and it was fine."
# --------------------------------------------------------------------------


def test_unanswered_findings_leave_everything_raised_and_say_so():
    result = compute_differential(CHEST_PAIN, {})
    assert len(result.items) == 14, "chest pain raises 14 possibilities"
    for item in result.items:
        assert item.status == RAISED
        assert "Not yet assessed" in item.reason


def test_empty_answers_exclude_nothing():
    """The failure this guards against is the whole project's governing
    principle: an untouched form must never read as a cleared differential."""
    result = compute_differential(CHEST_PAIN, {})
    assert not [i for i in result.items if i.status == EXCLUDED]


def test_answering_one_finding_leaves_the_others_untouched():
    """Partial completion is the normal case in a busy clinic. Items whose
    finding was never recorded must stay exactly as unassessed as they were."""
    result = _by_id(compute_differential(CHEST_PAIN, {"chest_wall_reproducible": False}))
    assert result["musculoskeletal_or_neuralgia"].status == EXCLUDED
    for other in ("pulmonary_embolism", "tb_pericarditis", "atrial_fibrillation"):
        assert result[other].status == RAISED
        assert "Not yet assessed" in result[other].reason


def test_an_unticked_symptom_never_carries_as_a_normal_finding():
    """Ticking 'murmur' on the symptom screen carries forward as a positive
    finding. NOT ticking it is 'not recorded', not 'auscultated and clear' --
    if that inverted, severe aortic stenosis would silently drop off every
    chest-pain patient who never had their heart listened to."""
    assert carried_findings(["murmur"]) == {"murmur": True}
    assert carried_findings(CHEST_PAIN) == {}
    assert _by_id(compute_differential(CHEST_PAIN, {}))["severe_aortic_stenosis"].status == RAISED


# --------------------------------------------------------------------------
# Rule 2 -- the killers never auto-exclude.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("item_id", sorted(KILLERS_NEEDING_CONFIRMATION))
def test_a_finding_that_argues_against_a_killer_does_not_drop_it(item_id):
    result = compute_differential(CHEST_PAIN, NORMAL_EXAM)
    item = _by_id(result)[item_id]
    assert item.status == PENDING_CONFIRMATION
    assert item.exclusion_policy == "confirm"
    assert "Unlikely" in item.reason


@pytest.mark.parametrize("item_id", sorted(KILLERS_NEEDING_CONFIRMATION))
def test_killer_drops_only_after_a_deliberate_confirmation(item_id):
    result = compute_differential(CHEST_PAIN, NORMAL_EXAM, [item_id])
    item = _by_id(result)[item_id]
    assert item.status == EXCLUDED
    assert "confirmed off the list" in item.reason


def test_one_finding_can_drop_a_tier_2_item_and_only_park_a_tier_1_item():
    """"No pleuritic pain" settles four possibilities at once -- and must not
    settle them all the same way. Pericarditis and pleuritis go; PE and
    pneumothorax are only parked. Consolidating the QUESTION must never
    consolidate the SAFETY BEHAVIOUR."""
    result = _by_id(compute_differential(CHEST_PAIN, {"pleuritic_pain": False}))
    assert result["pericarditis"].status == EXCLUDED
    assert result["pleuritis_or_pneumonitis"].status == EXCLUDED
    assert result["pulmonary_embolism"].status == PENDING_CONFIRMATION
    assert result["pneumothorax"].status == PENDING_CONFIRMATION


def test_confirmation_without_an_arguing_finding_does_nothing():
    """The tap confirms a finding that argues against the item. It is not a
    general-purpose 'remove this' button, so it must not override a finding
    that supports the item, nor act on one never recorded."""
    supported = compute_differential(CHEST_PAIN, {"pulses_equal": False}, ["aortic_dissection"])
    assert _by_id(supported)["aortic_dissection"].status == PROMOTED

    unanswered = compute_differential(CHEST_PAIN, {}, ["aortic_dissection"])
    assert _by_id(unanswered)["aortic_dissection"].status == RAISED


def test_exactly_the_four_killers_await_confirmation_after_a_normal_exam():
    assert set(pending_confirmation_ids(CHEST_PAIN, NORMAL_EXAM)) == KILLERS_NEEDING_CONFIRMATION


def test_confirmation_field_lists_only_what_is_pending():
    field = build_confirmation_field(CHEST_PAIN, NORMAL_EXAM)
    assert {o.value for o in field.options} == KILLERS_NEEDING_CONFIRMATION
    assert field.required is False, "confirming nothing must be a valid answer"


# --------------------------------------------------------------------------
# Rule 3 -- only examination can exclude, never the absence of a test.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("item_id", ["acs", "anaemia", "thyrotoxicosis", "reflux"])
def test_bedside_findings_cannot_clear_what_needs_a_test(item_id):
    """Every lever pulled at once -- a fully normal exam plus a confirming tap
    -- still must not remove these from the list."""
    result = compute_differential(CHEST_PAIN, NORMAL_EXAM, [item_id])
    item = _by_id(result)[item_id]
    assert item.status == RAISED
    assert item.exclusion_policy == "never"
    assert "does not clear it" in item.reason


def test_acs_is_never_excluded_by_this_engine():
    """ACS is handled formally inside the angina module's opening gate. The
    exclusion engine must not be able to take it off the list at all."""
    every_lever = compute_differential(
        CHEST_PAIN, NORMAL_EXAM, ["acs"] + sorted(KILLERS_NEEDING_CONFIRMATION)
    )
    assert _by_id(every_lever)["acs"].status != EXCLUDED


def test_questions_that_can_only_promote_are_marked_optional():
    """A question whose every item is exclusion_policy 'never' cannot take
    anything off the list, so the doctor is told it is optional rather than
    being made to answer it for nothing."""
    optional = {s.id for s in build_findings_field(CHEST_PAIN).findings if s.promotes_only}
    assert optional == {"pallor", "reflux_pattern"}


def test_skipping_the_optional_questions_costs_nothing_but_a_ranking():
    without = compute_differential(CHEST_PAIN, {k: v for k, v in NORMAL_EXAM.items() if k not in ("pallor", "reflux_pattern")})
    with_them = compute_differential(CHEST_PAIN, NORMAL_EXAM)
    assert {i.id for i in without.items if i.status == EXCLUDED} == {
        i.id for i in with_them.items if i.status == EXCLUDED
    }


# --------------------------------------------------------------------------
# Rule 4 -- a supporting finding promotes, it does not merely fail to exclude.
# --------------------------------------------------------------------------


def test_supporting_finding_promotes():
    result = compute_differential(CHEST_PAIN, {"pleuritic_pain": True})
    assert _by_id(result)["pericarditis"].status == PROMOTED
    assert _by_id(result)["pericarditis"].reason.startswith("Promoted")


def test_polarity_is_per_item_not_a_global_yes_means_bad():
    """Unequal pulses promote dissection; equal pulses argue against it. If
    polarity were hardcoded as "true is bad", asking the question the way a
    doctor actually asks it would invert the entire differential."""
    unequal = compute_differential(CHEST_PAIN, {"pulses_equal": False})
    assert _by_id(unequal)["aortic_dissection"].status == PROMOTED

    equal = compute_differential(CHEST_PAIN, {"pulses_equal": True})
    assert _by_id(equal)["aortic_dissection"].status == PENDING_CONFIRMATION


def test_one_finding_promotes_two_different_items():
    result = _by_id(compute_differential(CHEST_PAIN, {"constitutional": True}))
    assert result["tb_pericarditis"].status == PROMOTED, "the diagnosis a Western differential misses"
    assert result["thyrotoxicosis"].status == PROMOTED


def test_the_same_finding_promotes_one_item_while_arguing_against_another():
    """Exertional pain relieved by rest promotes angina. The same answer is
    what argues against ACS -- one question, opposite polarities, and ACS
    still cannot be excluded by it."""
    result = _by_id(compute_differential(CHEST_PAIN, {"exertional_relieved_by_rest": True}))
    assert result["stable_angina"].status == PROMOTED
    assert result["acs"].status == RAISED
    assert result["acs"].exclusion_policy == "never"

    at_rest = _by_id(compute_differential(CHEST_PAIN, {"exertional_relieved_by_rest": False}))
    assert at_rest["acs"].status == PROMOTED
    assert at_rest["stable_angina"].status == EXCLUDED


def test_a_carried_symptom_promotes_without_being_asked_again():
    result = _by_id(compute_differential(["murmur"], {}))
    assert result["severe_aortic_stenosis"].status == PROMOTED
    assert result["rhd"].status == PROMOTED


# --------------------------------------------------------------------------
# Consolidation -- the reason this layer exists in this shape at all.
# --------------------------------------------------------------------------


def test_chest_pain_asks_far_fewer_questions_than_it_raises_possibilities():
    """14 possibilities, 9 questions, 2 of them optional. A questionnaire the
    clinician abandons halfway through is not a safe one."""
    field = build_findings_field(CHEST_PAIN)
    assert len(raised_item_ids(CHEST_PAIN)) == 14
    assert len(field.findings) == 9
    assert sum(1 for s in field.findings if not s.promotes_only) == 7


def test_the_pleuritic_question_carries_four_possibilities_on_its_own():
    assert len(items_by_finding(CHEST_PAIN)["pleuritic_pain"]) == 4


def test_every_raised_item_is_reachable_by_some_question():
    """A possibility nobody can ever answer for is dead weight on the screen."""
    for symptom in ("chest_pain", "palpitations", "murmur", "fever_with_joint_pains"):
        covered = set(items_by_finding([symptom]))
        assert covered == set(findings_for([symptom]))
        reachable = {i for ids in items_by_finding([symptom]).values() for i in ids}
        assert reachable == set(raised_item_ids([symptom]))


def test_the_question_set_shrinks_with_the_presentation():
    """A fixed form asks everything every time. This one asks only what the
    selected symptoms actually raised."""
    assert len(findings_for(["irregular_pulse"])) == 1
    assert len(findings_for(CHEST_PAIN)) == 9


def test_findings_field_tells_the_doctor_what_each_question_buys():
    field = build_findings_field(CHEST_PAIN)
    by_id = {s.id: s for s in field.findings}
    assert by_id["pleuritic_pain"].resolves == [
        "Pulmonary embolism",
        "Pneumothorax",
        "Pericarditis",
        "Pleuritis or pneumonitis",
    ]
    assert all(s.question and s.short_label for s in field.findings)


def test_a_carried_finding_is_marked_prefilled_and_not_counted_as_a_question():
    field = build_findings_field(["chest_pain", "murmur"])
    by_id = {s.id: s for s in field.findings}
    assert by_id["murmur"].prefilled is True
    assert by_id["pleuritic_pain"].prefilled is False
    assert "6 observations" in field.description, "the carried one is not asked again"


# --------------------------------------------------------------------------
# What survives decides which modules open -- the router is an output.
# --------------------------------------------------------------------------


def test_excluded_item_withdraws_its_module():
    assert "angina_stable_v1" in compute_differential(CHEST_PAIN, {}).surviving_modules

    at_rest = compute_differential(CHEST_PAIN, {"exertional_relieved_by_rest": False})
    assert "angina_stable_v1" not in at_rest.surviving_modules


def test_pending_confirmation_still_counts_as_surviving():
    """A killer awaiting confirmation is still on the differential, so anything
    it would open stays eligible. 'Unlikely' must not behave like 'gone'."""
    result = compute_differential(CHEST_PAIN, NORMAL_EXAM)
    assert _by_id(result)["severe_aortic_stenosis"].status == PENDING_CONFIRMATION
    assert result.pending_confirmation


def test_rhd_module_survives_while_either_of_its_two_items_stands():
    both_gone = {"murmur": False, "fever_with_joint_pains": False}
    assert "rhd_v1" not in compute_differential(["fever_with_joint_pains"], both_gone).surviving_modules

    one_left = {"murmur": False}
    assert "rhd_v1" in compute_differential(["fever_with_joint_pains"], one_left).surviving_modules


# --------------------------------------------------------------------------
# The symptom -> possibility map, checked against plan/mock consult.md
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "symptom,count",
    [
        ("chest_pain", 14),
        ("exertional_breathlessness_or_fatigue", 8),
        ("palpitations", 4),
        ("fever_with_joint_pains", 2),
    ],
)
def test_symptom_raises_the_documented_number_of_possibilities(symptom, count):
    assert len(raised_item_ids([symptom])) == count


def test_selecting_more_symptoms_unions_the_lists():
    chest = set(raised_item_ids(["chest_pain"]))
    fever = set(raised_item_ids(["fever_with_joint_pains"]))
    both = set(raised_item_ids(["chest_pain", "fever_with_joint_pains"]))
    assert both == chest | fever
    assert both > chest


def test_items_come_back_worst_first():
    tiers = [ITEMS_BY_ID[i]["tier"] for i in raised_item_ids(CHEST_PAIN)]
    assert tiers == sorted(tiers), "ordered by what kills you if missed, not by what is likeliest"


def test_every_item_declares_an_exclusion_policy():
    """A new disease added without a policy would silently inherit the
    permissive default. The table must be explicit for all of them."""
    for item_id, item in ITEMS_BY_ID.items():
        assert item.get("exclusion_policy") in ("auto", "confirm", "never"), item_id
        assert item.get("exclusion_policy_reason"), f"{item_id} has no stated reason"


def test_every_item_declares_a_finding_that_exists():
    """A typo here would silently make an item permanently unanswerable, which
    reads on screen as 'still open' forever."""
    for item_id, item in ITEMS_BY_ID.items():
        link = item.get("finding")
        assert link, f"{item_id} has no finding"
        assert link["id"] in FINDINGS_BY_ID, f"{item_id} points at unknown finding {link['id']}"
        assert isinstance(link["supports_when"], bool), item_id
