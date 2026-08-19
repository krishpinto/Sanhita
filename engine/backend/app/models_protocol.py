"""
Pydantic models for a *protocol definition* -- the data-driven description of
a disease's intake questions, gates, parallel evidence tracks, and terminal
resolution table. No disease-specific field name ever appears in engine code;
everything the engine walks is one of the block types below, loaded from
protocols/*.json.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

Expr = Any  # a node in the app.engine.expr DSL -- arbitrarily nested JSON

FieldType = Literal[
    "boolean",
    "single_select",
    "multi_select",
    "text",
    "number",
    "structured_ecg",
    "structured_vitals",
    "differential_review",
    "findings_review",
]

AxisScore = Literal["positive", "negative", "partial_negative", "unknown"]
FieldSource = Literal["protocol", "core", "shared"]

# What kind of act the doctor needs to perform to answer this -- shown as a
# small badge on every question so there's never ambiguity about whether to
# ask the patient, examine them, pull a report, or use judgement. Distinct
# from FieldSource (which is a *storage* concept -- where the answer lives).
InputSource = Literal["history", "examination", "investigation", "clinical_judgement"]
INPUT_SOURCE_LABELS: dict[str, str] = {
    "history": "Ask the patient",
    "examination": "Examination finding",
    "investigation": "From investigation (ECG, echo, labs)",
    "clinical_judgement": "Clinical judgement",
}


class Option(BaseModel):
    value: str
    label: str


class Prefill(BaseModel):
    """Pulls a suggested starting value from elsewhere in the encounter (e.g.
    AF's rhythm-control substrate suggesting Angina's Track A resolution).
    Always just a starting value -- the doctor can override it."""

    source_path: str  # a namespace var path, e.g. "protocols.angina_stable_v1.tracks.track_a.resolution"
    value_map: dict[str, str] = Field(default_factory=dict)  # maps source value -> this field's option value
    default: str | None = None


class DifferentialItemSpec(BaseModel):
    """One row of a differential_review field -- a possibility the symptom
    set raised. Resolved by a single bedside-checkable yes/no question
    (discriminator_question), not by the clinician's free-form judgement --
    answering it is a factual observation, not a decision to exclude."""

    id: str
    label: str
    tier: int  # 1 = must not miss, 2 = consider, 3 = common and commonly the answer
    discriminator: str  # short clinical descriptor, used in the audit trail
    discriminator_question: str  # the actual yes/no prompt shown to the doctor
    discriminator_input_source: InputSource
    module: str | None = None  # protocol id this item opens if it survives, or None (no pathway in this build)
    # How a negative discriminator is allowed to act. "auto": absence rules it
    # out. "confirm": the killers -- absence makes it unlikely, never
    # impossible, so it needs one deliberate confirmation. "never": cannot be
    # cleared at the bedside at all (needs bloodwork, or is owned by another
    # module's gate); its discriminator can only ever promote.
    exclusion_policy: Literal["auto", "confirm", "never"] = "auto"


class FindingSpec(BaseModel):
    """One observation the doctor records on the findings screen. A finding is
    shared: "is the pain worse on breathing in?" is asked once and resolves
    four separate differential items. That sharing is the whole point -- asking
    one question per possibility relocates the tedium instead of removing it
    (private/context/vitalis-exclusion-engine.md).

    Three-state, always: true, false, or absent from the answer map meaning
    "not assessed". Never a two-state checkbox."""

    id: str
    question: str  # the prompt shown to the doctor
    short_label: str  # compact form, used in the audit trail
    input_source: InputSource
    help: str | None = None
    # Pre-answered "yes" when the doctor ticked this on the symptom screen.
    # Not ticked is NOT the same as absent, so it prefills nothing in that case.
    carried_from_symptom: str | None = None
    prefilled: bool = False
    # True when every item hanging off this finding has exclusion_policy
    # "never" -- the answer can only promote, so the question is genuinely
    # optional and is presented that way.
    promotes_only: bool = False
    resolves: list[str] = Field(default_factory=list)  # item labels, so the doctor can see what the question is buying


class FieldDef(BaseModel):
    id: str
    label: str
    field_type: FieldType
    description: str | None = None  # short plain-language helper text shown under the question
    input_source: InputSource | None = None  # "ask the patient" vs "exam" vs "investigation" vs "judgement"
    options: list[Option] = Field(default_factory=list)
    sub_fields: list["FieldDef"] = Field(default_factory=list)  # for structured_ecg / structured_vitals
    value_scoring: dict[str, AxisScore] = Field(default_factory=dict)  # axis fields only
    skip_when: Expr | None = None
    source: FieldSource = "protocol"
    shared_path: str | None = None  # when source == "shared"
    core_path: str | None = None  # when source == "core"
    prefill: Prefill | None = None
    required: bool = True
    vitalis_addition: bool = False
    vitalis_addition_reason: str | None = None
    differential_items: list[DifferentialItemSpec] = Field(default_factory=list)  # for field_type == "differential_review"
    findings: list[FindingSpec] = Field(default_factory=list)  # for field_type == "findings_review"


class AxisThreshold(BaseModel):
    min_positive: int
    label: str


class ResolutionRule(BaseModel):
    type: Literal["positive_axis_count"] = "positive_axis_count"
    thresholds: list[AxisThreshold]  # checked in list order; author must order descending


class NumericThreshold(BaseModel):
    when: Expr  # e.g. {">": [{"var": "core.vitals.hr"}, 110]}
    label: str
    flag: Literal["info", "caution", "emergency"] = "info"


class DecisionRow(BaseModel):
    when: Expr
    label: str


class TrackDef(BaseModel):
    id: str
    label: str
    description: str | None = None  # plain-language subtitle shown under the panel title
    mode: Literal[
        "axis_count", "any_true", "checklist_score", "numeric_thresholds", "single_choice", "decision_table"
    ]
    resolution_rule: ResolutionRule | None = None  # axis_count mode
    numeric_thresholds: list[NumericThreshold] = Field(default_factory=list)  # numeric_thresholds mode
    decision_rows: list[DecisionRow] = Field(default_factory=list)  # decision_table mode: first match wins,
    # rows may reference shared.* fields directly, not just this track's own `fields`
    fields: list[FieldDef] = Field(default_factory=list)  # scored fields
    display_fields: list[FieldDef] = Field(default_factory=list)  # supportive only, never scored


class DerivedTag(BaseModel):
    id: str
    label: str
    condition: Expr


class GateBlock(BaseModel):
    type: Literal["gate"] = "gate"
    id: str
    label: str
    description: str | None = None
    blocking: bool = True
    fields: list[FieldDef]
    fire_when: Expr
    terminal_code: str
    terminal_headline: str
    vitalis_addition: bool = False
    vitalis_addition_reason: str | None = None


class TrackGroupBlock(BaseModel):
    type: Literal["track_group"] = "track_group"
    id: str
    label: str
    tracks: list[TrackDef]


class DerivedTagsBlock(BaseModel):
    type: Literal["derived_tags"] = "derived_tags"
    id: str
    label: str
    tags: list[DerivedTag]


class ContextBlock(BaseModel):
    type: Literal["context"] = "context"
    id: str
    label: str
    description: str | None = None
    # "flag_positive": frontend highlights whichever fields answered true as an
    # "address before proceeding" list (e.g. potentiating factors). "plain":
    # rendered as an ordinary display list (e.g. risk-factor context).
    render_hint: Literal["plain", "flag_positive"] = "plain"
    fields: list[FieldDef]


class TerminalRow(BaseModel):
    when: Expr
    code: str
    headline: str


class TerminalTableBlock(BaseModel):
    type: Literal["terminal_table"] = "terminal_table"
    id: str
    label: str
    rows: list[TerminalRow]  # checked in order, first match wins
    default_code: str | None = None
    default_headline: str | None = None


class DrugInterlock(BaseModel):
    condition: Expr
    state: Literal["block", "caution"]
    reason: str
    vitalis_addition: bool = True  # per NN7: labelled as a Vitalis addition unless the source itself states it


class DrugEntry(BaseModel):
    id: str
    name: str
    dose: str
    group_label: str
    tiers: list[Literal["phc", "district", "tertiary"]] = Field(
        default_factory=lambda: ["phc", "district", "tertiary"]
    )
    applicable_when: Expr | None = None  # e.g. gated on which terminal the protocol resolved to
    interlocks: list[DrugInterlock] = Field(default_factory=list)
    quarantine_reason: str | None = None  # if set, never rendered in the normal list -- shown withheld, with reason
    note: str | None = None


class DrugRecommendationBlock(BaseModel):
    type: Literal["drug_recommendation"] = "drug_recommendation"
    id: str
    label: str
    facility_tier_path: str = "core.facility_tier"
    applicable_when: Expr | None = None  # whole block hidden (not just empty) until/unless this holds
    entries: list[DrugEntry]


Block = Annotated[
    GateBlock | TrackGroupBlock | DerivedTagsBlock | ContextBlock | TerminalTableBlock | DrugRecommendationBlock,
    Field(discriminator="type"),
]


class Activation(BaseModel):
    """A protocol can have either or both. `auto_trigger` forces activation
    the instant it's true, no consent asked (an objective finding that
    proves the diagnosis, e.g. AF's ECG rhythm -- 'the tracing can overrule
    the differential'). `offer_trigger` surfaces the module and waits for
    the doctor's consent (a differential-engine survival, or a supportive
    but non-diagnostic finding). auto is checked first and wins if both
    would fire."""

    auto_trigger: Expr | None = None
    offer_trigger: Expr | None = None


Fidelity = Literal["full", "reduced_fidelity_placeholder"]


class ProtocolDefinition(BaseModel):
    id: str
    name: str
    version: str
    source_citation: str
    fidelity: Fidelity = "full"
    fidelity_note: str | None = None
    activation: Activation
    blocks: list[Block]
