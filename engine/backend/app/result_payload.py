"""The parts of the result payload that more than one caller needs.

The result endpoint renders these for the doctor; the AI second opinion
renders them for a model. Both must see the same encounter -- an AI briefed
on a different summary than the one on screen would disagree with the engine
for reasons the doctor cannot check.
"""

from __future__ import annotations

import json
from typing import Any

from app.differential_engine import (
    FINDINGS_BY_ID,
    _effective_answers as _effective_findings,
    compute_differential,
    findings_for,
)
from app.engine_service import PROTOCOLS, NextStepResult
from app.models_db import Encounter


def core_summary(encounter: Encounter) -> dict[str, Any]:
    return {
        "name": encounter.patient_name,
        "age": encounter.patient_age,
        "sex": encounter.patient_sex,
        "facility_tier": encounter.facility_tier,
        "symptoms": json.loads(encounter.symptoms_json) if encounter.symptoms_json else [],
    }


def differential_audit(encounter: Encounter) -> dict | None:
    """Never let 'we didn't check' look like 'we checked and it was fine':
    every item the symptom set raised is listed here, whether it survived,
    was ruled out by its discriminator, or has no confirmatory module in this
    build ('still open') -- excluded is never rendered as absent, and each
    item carries the reason its status is what it is."""
    if not encounter.symptoms_json:
        return None
    symptoms = json.loads(encounter.symptoms_json)
    answers = json.loads(encounter.differential_answers_json) if encounter.differential_answers_json else {}
    confirmations = (
        json.loads(encounter.differential_confirmations_json)
        if encounter.differential_confirmations_json
        else []
    )
    result = compute_differential(symptoms, answers, confirmations)
    recorded = _effective_findings(symptoms, answers)
    return {
        "symptoms": symptoms,
        "findings": [
            {
                "id": fid,
                "question": FINDINGS_BY_ID[fid]["question"],
                "short_label": FINDINGS_BY_ID[fid]["short_label"],
                "answer": recorded.get(fid),  # None = not assessed, and stays that way in the record
                "carried_from_symptom": FINDINGS_BY_ID[fid].get("carried_from_symptom"),
            }
            for fid in findings_for(symptoms)
        ],
        "items": [
            {
                "id": i.id, "label": i.label, "tier": i.tier, "discriminator": i.discriminator,
                "module": i.module, "status": i.status, "reason": i.reason,
                "exclusion_policy": i.exclusion_policy, "finding": i.finding,
            }
            for i in result.items
        ],
        "surviving_modules": sorted(result.surviving_modules),
    }


def unrun_protocols(next_step: NextStepResult) -> list[dict[str, Any]]:
    """Every protocol this build knows that this encounter did not open, and
    why. A protocol the tool silently never mentions is indistinguishable, to
    the person reading the result, from one it ruled out."""
    ran_ids = {r.protocol_id for r in next_step.active_protocols}
    offered_ids = {o["protocol_id"] for o in next_step.offered_protocols}
    return [
        {
            "protocol_id": pid,
            "name": p.name,
            "reason": "offered_not_accepted" if pid in offered_ids else "not_triggered",
        }
        for pid, p in PROTOCOLS.items()
        if pid not in ran_ids
    ]
