"""Turns a raw answer into the sentence the clinician actually read and the
answer they actually gave, and appends it to the encounter's record.

Two rules govern everything in here:

1. Render at write time, never at read time. The field definition that
   produced the question is in hand at the moment the answer arrives; a year
   later, after the protocol has been revised, it is not. Storing the raw
   value alone would leave the record open to being re-rendered against a
   question that has since changed wording -- a record that shifts under you
   is not a record.

2. One field can be many questions. The findings screen is nine observations
   behind a single answer path, and the ECG is a dozen. Flattening those to
   "differential_answers: 8 of 9 recorded" hides exactly what the doctor
   wants to check. Every question the doctor answered gets its own line.

Nothing in this module is ever read back by the engine.
"""

from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session, func, select

from app.models_db import AnswerEvent
from app.models_protocol import FieldDef

# What a three-state finding reads as. "Not assessed" is a real answer and is
# recorded as one -- the whole safety model rests on it never being allowed to
# quietly render as "No".
_NOT_ASSESSED = "Not assessed"


def _scalar(field: FieldDef, value: Any) -> str:
    if value is None or value == "":
        return "Not recorded"
    if field.field_type == "boolean" or isinstance(value, bool):
        return "Yes" if value is True else "No"
    if field.options:
        for option in field.options:
            if option.value == value:
                return option.label
    return str(value)


def render_entries(field: FieldDef, value: Any) -> list[dict[str, str]]:
    """The clinician-readable form of one submitted answer, as one or more
    {question, answer} pairs."""
    kind = field.field_type

    if kind == "findings_review":
        answers = value if isinstance(value, dict) else {}
        return [
            {
                "question": spec.question,
                "answer": _NOT_ASSESSED if answers.get(spec.id) is None else ("Yes" if answers[spec.id] else "No"),
            }
            for spec in field.findings
        ]

    if kind in ("structured_ecg", "structured_vitals"):
        data = value if isinstance(value, dict) else {}
        rows = [
            {"question": sub.label, "answer": _scalar(sub, data[sub.id])}
            for sub in field.sub_fields
            if data.get(sub.id) is not None and data.get(sub.id) != ""
        ]
        return rows or [{"question": field.label, "answer": "Not recorded"}]

    if kind == "multi_select":
        chosen = list(value) if isinstance(value, list) else []
        if not chosen:
            # For the tier-1 confirmation step this is the important answer,
            # not an empty one: nothing was taken off the list.
            return [{"question": field.label, "answer": "None selected"}]
        labels = {option.value: option.label for option in field.options}
        return [{"question": field.label, "answer": ", ".join(labels.get(c, str(c)) for c in chosen)}]

    if kind == "differential_review":
        return [{"question": field.label, "answer": "Reviewed"}]

    return [{"question": field.label, "answer": _scalar(field, value)}]


def record(
    session: Session,
    encounter_id: str,
    field_path: str,
    field: FieldDef,
    value: Any,
    *,
    protocol_id: str = "core",
    block_label: str | None = None,
    previous_entries: list[dict[str, str]] | None = None,
) -> None:
    next_seq = (
        session.exec(
            select(func.coalesce(func.max(AnswerEvent.seq), 0)).where(AnswerEvent.encounter_id == encounter_id)
        ).one()
        + 1
    )
    session.add(
        AnswerEvent(
            encounter_id=encounter_id,
            seq=next_seq,
            field_path=field_path,
            protocol_id=protocol_id,
            block_label=block_label,
            field_label=field.label,
            value_json=json.dumps(value),
            entries_json=json.dumps(render_entries(field, value)),
            is_correction=previous_entries is not None,
            previous_entries_json=json.dumps(previous_entries) if previous_entries is not None else None,
        )
    )
    session.commit()


def transcript(session: Session, encounter_id: str) -> list[dict[str, Any]]:
    """Everything entered, in the order it was entered. Corrections appear as
    their own entries rather than overwriting what they replaced -- an audit
    trail that edits itself is not one."""
    rows = session.exec(
        select(AnswerEvent).where(AnswerEvent.encounter_id == encounter_id).order_by(AnswerEvent.seq)
    ).all()
    return [
        {
            "seq": row.seq,
            "field_path": row.field_path,
            "protocol_id": row.protocol_id,
            "block_label": row.block_label,
            "field_label": row.field_label,
            "entries": json.loads(row.entries_json),
            "is_correction": row.is_correction,
            "previous_entries": json.loads(row.previous_entries_json) if row.previous_entries_json else None,
            "answered_at": row.answered_at.isoformat(),
        }
        for row in rows
    ]
