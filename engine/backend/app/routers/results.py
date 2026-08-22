import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.answer_log import transcript
from app.auth import get_encounter_for_path
from app.db import get_session
from app.differential_engine import (
    FINDINGS_BY_ID,
    _effective_answers as _effective_findings,
    compute_differential,
    findings_for,
)
from app.engine_service import PROTOCOLS, compute_next_step, serialize_protocol_result
from app.models_db import AiOpinion, DoctorOpinion, Encounter

router = APIRouter(prefix="/encounters", tags=["results"])


@router.get("/{encounter_id}/result")
def get_result(
    encounter: Encounter = Depends(get_encounter_for_path),
    session: Session = Depends(get_session),
) -> dict:
    next_step = compute_next_step(session, encounter)

    if next_step.core_terminal:
        return {
            "core_terminal": next_step.core_terminal,
            "core": _core_summary(encounter),
            "differential": None,
            "protocols": [],
            "unrun_protocols": [],
            "answer_log": transcript(session, encounter.id),
            "ai_opinion": None,
            "doctor_opinion": None,
        }

    if not next_step.ready_for_result:
        raise HTTPException(status.HTTP_409_CONFLICT, "No protocol has reached a result yet")

    ran_ids = {r.protocol_id for r in next_step.active_protocols}
    offered_ids = {o["protocol_id"] for o in next_step.offered_protocols}
    unrun = [
        {"protocol_id": pid, "name": p.name, "reason": "offered_not_accepted" if pid in offered_ids else "not_triggered"}
        for pid, p in PROTOCOLS.items()
        if pid not in ran_ids
    ]

    ai_opinion = session.exec(
        select(AiOpinion).where(AiOpinion.encounter_id == encounter.id).order_by(AiOpinion.requested_at.desc())
    ).first()
    doctor_opinion = session.exec(
        select(DoctorOpinion).where(DoctorOpinion.encounter_id == encounter.id)
    ).first()

    return {
        "core_terminal": None,
        "core": _core_summary(encounter),
        "differential": _differential_audit(encounter),
        "protocols": [serialize_protocol_result(r) for r in next_step.active_protocols],
        "unrun_protocols": unrun,
        # Everything the clinician typed or tapped, in order, corrections
        # included. A routing recommendation nobody can check the inputs of is
        # not decision support.
        "answer_log": transcript(session, encounter.id),
        "ai_opinion": _serialize_ai_opinion(ai_opinion),
        "doctor_opinion": _serialize_doctor_opinion(doctor_opinion),
    }


def _core_summary(encounter: Encounter) -> dict:
    return {
        "name": encounter.patient_name,
        "age": encounter.patient_age,
        "sex": encounter.patient_sex,
        "symptoms": json.loads(encounter.symptoms_json) if encounter.symptoms_json else [],
    }


def _differential_audit(encounter: Encounter) -> dict | None:
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


def _serialize_ai_opinion(row: AiOpinion | None) -> dict | None:
    if row is None:
        return None
    return {
        "provider": row.provider,
        "status": row.status,
        "content": row.content,
        "reason": row.reason,
        "requested_at": row.requested_at.isoformat(),
        "responded_at": row.responded_at.isoformat() if row.responded_at else None,
    }


def _serialize_doctor_opinion(row: DoctorOpinion | None) -> dict | None:
    if row is None:
        return None
    return {
        "doctor_note": row.doctor_note,
        "structured_alternate_diagnosis": row.structured_alternate_diagnosis,
        "updated_at": row.updated_at.isoformat(),
    }
