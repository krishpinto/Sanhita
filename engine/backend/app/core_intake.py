"""The fixed 4-step intake sequence (patient details -> primary symptom ->
ECG -> vitals). Deliberately NOT protocol-loaded data -- this is the one part
of the encounter that's the same for every disease, so it's a small fixed
schema in code rather than something a future protocol author would ever
need to touch.

Also owns the two bits of logic the spec calls out as core (not per-protocol)
rules: the ST-elevation hard exit, and the three-state ECG availability rule
(an ECG that wasn't reviewed makes its findings UNKNOWN, never silently
ABSENT)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.models_protocol import FieldDef

_CORE_INTAKE_PATH = Path(__file__).resolve().parent / "core_intake.json"

_ECG_FINDING_FIELDS = [
    "rhythm",
    "rate",
    "q_waves",
    "st_t_changes",
    "st_elevation",
    "bbb",
    "chamber_enlargement",
    "pre_excitation",
    "qt_interval",
]
_ECG_BOOLEAN_FINDINGS = {"q_waves", "st_t_changes", "st_elevation", "bbb", "chamber_enlargement", "pre_excitation"}


@dataclass
class CoreStep:
    id: str
    label: str
    description: str | None
    fields: list[FieldDef]


def load_core_steps() -> list[CoreStep]:
    raw = json.loads(_CORE_INTAKE_PATH.read_text(encoding="utf-8"))
    return [
        CoreStep(
            id=s["id"], label=s["label"], description=s.get("description"),
            fields=[FieldDef.model_validate(f) for f in s["fields"]],
        )
        for s in raw["steps"]
    ]


CORE_STEPS = load_core_steps()


def project_ecg_finding(ecg_answer: dict[str, Any]) -> dict[str, Any]:
    """Applies the three-state ECG availability rule: findings are only
    trustworthy as ABSENT when the ECG was actually performed and reviewed.
    Otherwise every finding is left out of the projection entirely, which is
    exactly what makes it 'unknown' (not determinable) to the expression
    engine rather than silently false."""
    availability = ecg_answer.get("availability")
    projected: dict[str, Any] = {"availability": availability}
    if availability != "performed_reviewed":
        return projected  # findings unknown -- deliberately omitted, not defaulted to absent
    for key in _ECG_FINDING_FIELDS:
        value = ecg_answer.get(key)
        if value is None and key in _ECG_BOOLEAN_FINDINGS:
            value = False  # unticked, on a reviewed ECG, means absent
        if value is not None:
            projected[key] = value
    return projected


def check_st_elevation_hard_exit(ecg_answer: dict[str, Any]) -> dict[str, str] | None:
    projected = project_ecg_finding(ecg_answer)
    if projected.get("st_elevation") is True:
        return {
            "code": "ST_ELEVATION_SUSPECTED_STEMI",
            "headline": (
                "ST elevation on ECG — treat as suspected STEMI. Hard exit before Gate 0; "
                "no protocol runs. Refer per STEMI pathway immediately."
            ),
        }
    return None
