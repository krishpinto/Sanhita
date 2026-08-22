"""SQLite persistence. Seven tables, deliberately no more: no persisted
derived-value cache (the engine recomputes from raw answers on every read)
and no migrations tooling (create_all() against a fresh file is enough for a
prototype)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Encounter(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    access_token: str = Field(unique=True, index=True)
    status: str = Field(default="intake")  # intake | in_progress | completed
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    facility_tier: str | None = None  # session setting: phc | district | tertiary -- gates all drug/tier filtering
    patient_name: str | None = None
    patient_age: int | None = None
    patient_sex: str | None = None
    symptoms_json: str | None = None  # JSON-encoded list[str] -- multi-select, v0.4: never just one chief complaint

    ecg_json: str | None = None  # JSON-encoded structured ECG findings
    vitals_json: str | None = None  # JSON-encoded structured vitals, optional

    # v0.4 differential engine: symptoms raise a tiered DDx list; each item is
    # resolved by one bedside discriminator question, not clinician judgement;
    # survivors decide which modules open. The router is an output, not the
    # first decision.
    differential_answers_json: str | None = None  # JSON-encoded dict[item_id, bool] -- True=present, False=ruled out, absent=not yet assessed
    # Rule 2: the killers never auto-exclude. A negative discriminator on a
    # tier-1 item parks it in pending_confirmation; this is the deliberate
    # second act that actually drops it. Stored separately from the finding
    # above precisely so observing and excluding stay two different records.
    differential_confirmations_json: str | None = None  # JSON-encoded list[item_id] the clinician confirmed off the list

    core_terminal_code: str | None = None  # e.g. ST-elevation hard exit, before any protocol runs
    core_terminal_headline: str | None = None


class SharedClinicalHistoryEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    encounter_id: str = Field(foreign_key="encounter.id", index=True)
    field_id: str
    value_json: str  # JSON-encoded value
    answered_at: datetime = Field(default_factory=_now)


class ProtocolActivation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    encounter_id: str = Field(foreign_key="encounter.id", index=True)
    protocol_id: str
    protocol_version: str
    activation_mode: str  # "auto" | "offered_accepted"
    status: str = Field(default="active")  # active | resolved
    terminal_code: str | None = None
    terminal_headline: str | None = None
    activated_at: datetime = Field(default_factory=_now)


class Answer(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    protocol_activation_id: int = Field(foreign_key="protocolactivation.id", index=True)
    field_path: str = Field(index=True)
    raw_value_json: str  # JSON-encoded value
    answered_at: datetime = Field(default_factory=_now)


class AiOpinion(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    encounter_id: str = Field(foreign_key="encounter.id", index=True)
    provider: str
    status: str  # "unavailable" | "success" | "error"
    content: str | None = None
    reason: str | None = None
    requested_at: datetime = Field(default_factory=_now)
    responded_at: datetime | None = None


class DoctorOpinion(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    encounter_id: str = Field(foreign_key="encounter.id", index=True, unique=True)
    doctor_note: str | None = None
    structured_alternate_diagnosis: str | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class AnswerEvent(SQLModel, table=True):
    """Append-only witness of everything the clinician entered, in the order
    they entered it -- including answers they later changed.

    The engine never reads this table. It still recomputes every result from
    the live answer tables above; this is a record, not a source. It exists
    because two things need it and neither is the engine: a finished
    consultation has to be able to show the doctor every question they were
    asked and what they answered, and once answers can be corrected, "what did
    it say before I changed it" becomes part of the clinical record rather
    than a curiosity.

    `entries_json` is the human rendering done at write time, while the field
    definition that produced the question is still in hand: a list of
    {question, answer} pairs. One pair for a simple field; one per finding for
    the findings screen; one per recorded sub-field for the ECG.
    """

    id: int | None = Field(default=None, primary_key=True)
    encounter_id: str = Field(foreign_key="encounter.id", index=True)
    seq: int  # order within the encounter, corrections included
    field_path: str = Field(index=True)
    protocol_id: str = Field(default="core")
    block_label: str | None = None
    field_label: str
    value_json: str
    entries_json: str  # JSON list of {"question": str, "answer": str}
    # A correction carries what it replaced, so the record shows the change
    # rather than quietly presenting the new answer as if it were the first.
    is_correction: bool = Field(default=False)
    previous_entries_json: str | None = None
    answered_at: datetime = Field(default_factory=_now)
