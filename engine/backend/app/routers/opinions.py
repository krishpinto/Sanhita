import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.ai.base import SecondOpinionContext
from app.ai.factory import get_ai_provider
from app.auth import get_encounter_for_path
from app.db import get_session
from app.engine_service import compute_next_step, serialize_protocol_result
from app.models_api import DoctorOpinionRequest
from app.models_db import AiOpinion, DoctorOpinion, Encounter

router = APIRouter(prefix="/encounters", tags=["opinions"])


@router.post("/{encounter_id}/ai-opinion")
async def post_ai_opinion(
    encounter: Encounter = Depends(get_encounter_for_path),
    session: Session = Depends(get_session),
) -> dict:
    next_step = compute_next_step(session, encounter)
    if not next_step.ready_for_result:
        raise HTTPException(status.HTTP_409_CONFLICT, "No protocol has reached a result yet")

    provider = get_ai_provider()
    ctx = SecondOpinionContext(
        core={
            "age": encounter.patient_age,
            "sex": encounter.patient_sex,
            "symptoms": json.loads(encounter.symptoms_json) if encounter.symptoms_json else [],
        },
        protocols=[serialize_protocol_result(r) for r in next_step.active_protocols],
    )
    requested_at = datetime.now(timezone.utc)
    result = await provider.generate(ctx)

    row = AiOpinion(
        encounter_id=encounter.id,
        provider=provider.name,
        status=result.status,
        content=result.content,
        reason=result.reason,
        requested_at=requested_at,
        responded_at=datetime.now(timezone.utc),
    )
    session.add(row)
    session.commit()

    return {
        "provider": row.provider,
        "status": row.status,
        "content": row.content,
        "reason": row.reason,
        "disclaimer": (
            "This is an AI-generated second opinion, not a diagnosis. "
            "Weigh it alongside your own clinical judgement -- agree or disagree as you see fit."
        ),
    }


@router.post("/{encounter_id}/doctor-opinion")
def post_doctor_opinion(
    body: DoctorOpinionRequest,
    encounter: Encounter = Depends(get_encounter_for_path),
    session: Session = Depends(get_session),
) -> dict:
    existing = session.exec(select(DoctorOpinion).where(DoctorOpinion.encounter_id == encounter.id)).first()
    now = datetime.now(timezone.utc)
    if existing:
        existing.doctor_note = body.doctor_note
        existing.structured_alternate_diagnosis = body.structured_alternate_diagnosis
        existing.updated_at = now
        session.add(existing)
    else:
        session.add(
            DoctorOpinion(
                encounter_id=encounter.id,
                doctor_note=body.doctor_note,
                structured_alternate_diagnosis=body.structured_alternate_diagnosis,
                updated_at=now,
            )
        )
    session.commit()
    return {"ok": True}
