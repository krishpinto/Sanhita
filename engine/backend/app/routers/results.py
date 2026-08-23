from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.answer_log import transcript
from app.auth import get_encounter_for_path
from app.db import get_session
from app.engine_service import compute_next_step, serialize_protocol_result
from app.models_db import AiOpinion, DoctorOpinion, Encounter
from app.result_payload import core_summary, differential_audit, unrun_protocols

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
            "core": core_summary(encounter),
            "differential": None,
            "protocols": [],
            "unrun_protocols": [],
            "answer_log": transcript(session, encounter.id),
            "ai_opinion": None,
            "doctor_opinion": None,
        }

    if not next_step.ready_for_result:
        raise HTTPException(status.HTTP_409_CONFLICT, "No protocol has reached a result yet")

    unrun = unrun_protocols(next_step)

    ai_opinion = session.exec(
        select(AiOpinion).where(AiOpinion.encounter_id == encounter.id).order_by(AiOpinion.requested_at.desc())
    ).first()
    doctor_opinion = session.exec(
        select(DoctorOpinion).where(DoctorOpinion.encounter_id == encounter.id)
    ).first()

    return {
        "core_terminal": None,
        "core": core_summary(encounter),
        "differential": differential_audit(encounter),
        "protocols": [serialize_protocol_result(r) for r in next_step.active_protocols],
        "unrun_protocols": unrun,
        # Everything the clinician typed or tapped, in order, corrections
        # included. A routing recommendation nobody can check the inputs of is
        # not decision support.
        "answer_log": transcript(session, encounter.id),
        "ai_opinion": _serialize_ai_opinion(ai_opinion),
        "doctor_opinion": _serialize_doctor_opinion(doctor_opinion),
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
