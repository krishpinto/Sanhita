"""
v0.4's inversion: symptoms in, differential out, and the surviving
possibilities decide which confirmatory modules open -- the router is an
output, not the first decision.

Loads the symptom -> differential-item table (differential_table.json) and
provides pure functions over it. Deliberately not part of app/engine/ --
this is a Part 2 (shared intake layer) concern, not a per-protocol concern;
protocols never see raw symptoms, only the surviving_modules set this
module computes.

The doctor answers FINDINGS, not possibilities. A finding is shared: "is the
pain worse on breathing in?" is asked once and settles pulmonary embolism,
pneumothorax, pericarditis and pleuritis together. One question per
possibility would relocate the tedium rather than remove it, and a
questionnaire the clinician abandons halfway through is not a safe one
(private/context/vitalis-exclusion-engine.md).

The four rules this module exists to enforce (private/context/READ-THIS-FIRST.md section 4):

  1. Never let "we didn't check" look like "we checked and it was fine."
     A finding absent from the answer map leaves every item hanging off it
     raised and flagged unassessed. Three states, never two.
  2. The killers never auto-exclude. A finding that argues against them makes
     them unlikely, not impossible, so `exclusion_policy: "confirm"` items
     sit in `pending_confirmation` until the doctor deliberately drops them.
  3. Only examination can exclude, never the absence of a test.
     `exclusion_policy: "never"` items cannot be cleared at the bedside at
     all -- their finding can only ever promote them. Where every item on a
     finding is "never", the whole question is optional: answering it can
     move something up the list but can never take anything off it.
  4. A finding that supports an item PROMOTES it, it doesn't merely fail to
     exclude. Note that "supports" is per-item and not always the same as
     "yes": equal pulses (true) argue AGAINST dissection, so dissection
     declares supports_when=false. Polarity lives in the table, not in code.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from app.models_protocol import DifferentialItemSpec, FieldDef, FindingSpec, Option

_TABLE_PATH = Path(__file__).resolve().parent / "differential_table.json"
_TABLE = json.loads(_TABLE_PATH.read_text(encoding="utf-8"))

SYMPTOMS: list[dict] = _TABLE["symptoms"]
ITEMS_BY_ID: dict[str, dict] = {i["id"]: i for i in _TABLE["items"]}
SYMPTOM_ITEM_MAP: dict[str, list[str]] = _TABLE["symptom_item_map"]
FINDINGS: list[dict] = _TABLE["findings"]
FINDINGS_BY_ID: dict[str, dict] = {f["id"]: f for f in FINDINGS}

# Status values. Only "excluded" removes an item from the differential; every
# other status keeps it standing, and therefore keeps its module eligible.
PROMOTED = "promoted"
RAISED = "raised"
PENDING_CONFIRMATION = "pending_confirmation"
EXCLUDED = "excluded"


def _policy(item: dict) -> str:
    """Tier-derived fallback so a table row that predates exclusion_policy can
    never silently default to the permissive behaviour: an unlabelled Tier 1
    item requires confirmation rather than auto-excluding."""
    declared = item.get("exclusion_policy")
    if declared in ("auto", "confirm", "never"):
        return declared
    return "confirm" if item["tier"] == 1 else "auto"


def _link(item: dict) -> tuple[str, bool]:
    """(finding id, the answer that argues FOR this item)."""
    link = item["finding"]
    return link["id"], link["supports_when"]


@dataclass
class DifferentialItemState:
    id: str
    label: str
    tier: int
    discriminator: str
    module: str | None
    status: str  # promoted | raised | pending_confirmation | excluded
    reason: str  # always populated -- excluded is never silent, "not yet assessed" is never mistaken for "checked and negative"
    exclusion_policy: str = "auto"
    finding: str = ""  # the finding id that settled it, for the audit trail


@dataclass
class DifferentialResult:
    items: list[DifferentialItemState]  # every raised item, tier order then label order
    surviving_modules: set[str]  # module ids with >=1 surviving (non-excluded) item
    pending_confirmation: list[DifferentialItemState] = field(default_factory=list)


def raised_item_ids(symptoms: list[str]) -> list[str]:
    """Union of every item any selected symptom can raise, deduplicated,
    stable order (tier, then declaration order)."""
    seen: set[str] = set()
    for s in symptoms:
        for item_id in SYMPTOM_ITEM_MAP.get(s, []):
            seen.add(item_id)
    return [i["id"] for i in _TABLE["items"] if i["id"] in seen]


# ---------------------------------------------------------------- findings


def items_by_finding(symptoms: list[str]) -> dict[str, list[str]]:
    """finding id -> the item ids it settles for this symptom set."""
    grouped: dict[str, list[str]] = {}
    for item_id in raised_item_ids(symptoms):
        finding_id, _ = _link(ITEMS_BY_ID[item_id])
        grouped.setdefault(finding_id, []).append(item_id)
    return grouped


def findings_for(symptoms: list[str]) -> list[str]:
    """The findings worth asking about, in table order. A finding whose items
    were not raised is never shown -- the question set shrinks with the
    presentation rather than being a fixed form."""
    needed = items_by_finding(symptoms)
    return [f["id"] for f in FINDINGS if f["id"] in needed]


def _is_optional(finding_id: str, item_ids: Iterable[str]) -> bool:
    """A question is optional when nothing it could answer would ever be
    removed by it -- every item hanging off it is exclusion_policy "never".
    Rule 3: no bedside finding clears those, so the doctor is told plainly
    that skipping this costs them nothing but a ranking."""
    if FINDINGS_BY_ID[finding_id].get("promotes_only"):
        return True
    return all(_policy(ITEMS_BY_ID[i]) == "never" for i in item_ids)


def carried_findings(symptoms: list[str]) -> dict[str, bool]:
    """Findings already answered on the symptom screen. Ticking 'murmur' is
    the same observation as answering the murmur finding, so it carries and is
    not asked twice.

    Deliberately one-directional: a symptom NOT ticked does not carry as
    False. Rule 1 -- an unticked box is 'not recorded', not 'examined and
    normal', and the difference is the whole project."""
    carried: dict[str, bool] = {}
    for finding_id in findings_for(symptoms):
        source = FINDINGS_BY_ID[finding_id].get("carried_from_symptom")
        if source and source in symptoms:
            carried[finding_id] = True
    return carried


def build_findings_field(symptoms: list[str], answers: dict[str, bool] | None = None) -> FieldDef:
    """The screen the doctor actually works through: a handful of factual
    observations, each of which may settle several possibilities at once.

    They are never asked "have you excluded dissection?" -- they are asked
    "are the pulses equal in both arms?". The system already knows what equal
    pulses mean. The doctor observes; the machine reasons."""
    answers = answers or {}
    carried = carried_findings(symptoms)
    grouped = items_by_finding(symptoms)

    specs: list[FindingSpec] = []
    for finding_id in findings_for(symptoms):
        f = FINDINGS_BY_ID[finding_id]
        item_ids = grouped[finding_id]
        specs.append(
            FindingSpec(
                id=finding_id,
                question=f["question"],
                short_label=f["short_label"],
                input_source=f["input_source"],
                help=f.get("help"),
                carried_from_symptom=f.get("carried_from_symptom"),
                prefilled=finding_id in carried and finding_id not in answers,
                promotes_only=_is_optional(finding_id, item_ids),
                resolves=[ITEMS_BY_ID[i]["label"] for i in item_ids],
            )
        )

    required_count = sum(1 for s in specs if not s.promotes_only and not s.prefilled)
    return FieldDef(
        id="differential_answers",
        label="What can you see?",
        field_type="findings_review",
        input_source="examination",
        description=(
            f"{required_count} observations settle the list above. Answer what you have actually "
            "checked - anything you leave blank stays open rather than being counted as normal. "
            "Questions marked optional can only move something up the list, never take it off."
        ),
        required=False,
        findings=specs,
        # The raised differential travels with the questions so the client can
        # show the list first and the questions second, on one screen or two.
        differential_items=build_differential_review_field(symptoms).differential_items,
    )


# ------------------------------------------------------- the differential


def build_differential_review_field(symptoms: list[str]) -> FieldDef:
    """The read-only list the doctor sees before answering anything: every
    possibility the symptom set raises, worst-first, each showing which
    finding will settle it. Display only -- the answers come from
    build_findings_field."""
    items = [
        DifferentialItemSpec(
            id=item_id,
            label=ITEMS_BY_ID[item_id]["label"],
            tier=ITEMS_BY_ID[item_id]["tier"],
            discriminator=ITEMS_BY_ID[item_id]["discriminator"],
            discriminator_question=FINDINGS_BY_ID[_link(ITEMS_BY_ID[item_id])[0]]["question"],
            discriminator_input_source=ITEMS_BY_ID[item_id]["discriminator_input_source"],
            module=ITEMS_BY_ID[item_id]["module"],
            exclusion_policy=_policy(ITEMS_BY_ID[item_id]),
        )
        for item_id in raised_item_ids(symptoms)
    ]
    return FieldDef(
        id="differential_review",
        label="Review the differential",
        field_type="differential_review",
        input_source="clinical_judgement",
        description=(
            "Based on what you selected, these are the possibilities worth considering, ordered by "
            "what it costs to miss them. You don't rule any of them out here - the next screen asks "
            "for findings, and the system does the ruling out."
        ),
        required=False,
        differential_items=items,
    )


def _effective_answers(symptoms: list[str], answers: dict[str, bool] | None) -> dict[str, bool]:
    merged = dict(carried_findings(symptoms))
    merged.update(answers or {})
    return merged


def pending_confirmation_ids(symptoms: list[str], answers: dict[str, bool] | None = None) -> list[str]:
    """Items whose finding argues against them but whose policy forbids acting
    on that alone -- the killers. Rule 2: these need one deliberate tap each
    before they leave the differential."""
    findings = _effective_answers(symptoms, answers)
    out = []
    for item_id in raised_item_ids(symptoms):
        item = ITEMS_BY_ID[item_id]
        finding_id, supports = _link(item)
        answer = findings.get(finding_id)
        if answer is not None and answer is not supports and _policy(item) == "confirm":
            out.append(item_id)
    return out


def build_confirmation_field(symptoms: list[str], answers: dict[str, bool] | None = None) -> FieldDef:
    """Rule 2 made explicit as its own step. Observing "pulses are equal" and
    deciding "I am taking dissection off the list" are two different acts, and
    keeping them two different questions is the safety property -- the doctor
    is never asked to exclude something as a side effect of reporting a
    finding. Confirming nothing is a valid answer; those items simply stay up."""
    pending = pending_confirmation_ids(symptoms, answers)
    findings = _effective_answers(symptoms, answers)
    options = []
    for item_id in pending:
        item = ITEMS_BY_ID[item_id]
        finding_id, _ = _link(item)
        f = FINDINGS_BY_ID[finding_id]
        said = "Yes" if findings.get(finding_id) else "No"
        options.append(Option(value=item_id, label=f"{item['label']} - {f['short_label']}: {said}"))
    return FieldDef(
        id="differential_confirmations",
        label="Confirm before dropping these",
        field_type="multi_select",
        input_source="clinical_judgement",
        description=(
            "Your examination findings argue against each of these, but a normal examination makes them "
            "unlikely - not impossible. Tick only the ones you are deliberately taking off the list. "
            "Anything left unticked stays on it."
        ),
        required=False,
        options=options,
    )


def compute_differential(
    symptoms: list[str],
    answers: dict[str, bool] | None = None,
    confirmations: Iterable[str] | None = None,
) -> DifferentialResult:
    """answers: {finding_id: True|False}. A finding absent from the map is
    "not assessed" -- it leaves every item hanging off it standing.

    confirmations: item ids the doctor has deliberately dropped. Only consulted
    for `exclusion_policy: "confirm"` items -- confirming an item whose finding
    supports it, or is unanswered, does nothing, because the tap confirms a
    negative finding rather than overriding a positive one."""
    findings = _effective_answers(symptoms, answers)
    confirmed = set(confirmations or ())
    items: list[DifferentialItemState] = []
    surviving_modules: set[str] = set()
    pending: list[DifferentialItemState] = []

    for item_id in raised_item_ids(symptoms):
        item = ITEMS_BY_ID[item_id]
        policy = _policy(item)
        finding_id, supports = _link(item)
        spec = FINDINGS_BY_ID[finding_id]
        answer = findings.get(finding_id)
        # How this item's finding reads in a sentence, e.g. "Pleuritic pain: Yes".
        said = f"{spec['short_label']}: {'Yes' if answer else 'No'}"

        if answer is None:
            status = RAISED
            reason = f"Not yet assessed - {spec['short_label'].lower()} not recorded. Kept open."
        elif answer is supports:
            # Rule 4 -- a supporting finding promotes, it does not merely fail to exclude.
            status = PROMOTED
            reason = f"Promoted - {said}."
        elif policy == "auto":
            status = EXCLUDED
            reason = f"Ruled out - {said}."
        elif policy == "confirm":
            if item_id in confirmed:
                status = EXCLUDED
                reason = f"Ruled out - {said}, and confirmed off the list by the clinician."
            else:
                # Rule 2 -- unlikely is not impossible. Stays on the list.
                status = PENDING_CONFIRMATION
                reason = (
                    f"Unlikely - {said}. Still listed: a normal examination does not exclude this, "
                    "so it needs a deliberate confirmation to drop."
                )
        else:  # policy == "never"
            # Rule 3 -- only examination can exclude, and this one examination cannot.
            status = RAISED
            extra = item.get("exclusion_policy_reason", "")
            reason = f"Still open - {said}, but that does not clear it. {extra}".strip()

        state = DifferentialItemState(
            id=item_id,
            label=item["label"],
            tier=item["tier"],
            discriminator=item["discriminator"],
            module=item["module"],
            status=status,
            reason=reason,
            exclusion_policy=policy,
            finding=finding_id,
        )
        items.append(state)
        if status == PENDING_CONFIRMATION:
            pending.append(state)
        if status != EXCLUDED and item["module"]:
            surviving_modules.add(item["module"])

    return DifferentialResult(items=items, surviving_modules=surviving_modules, pending_confirmation=pending)
