from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.auth import get_encounter_for_path
from app.db import get_session
from app.engine_service import compute_next_step, serialize_next_step, submit_answer
from app.models_api import AnswerRequest
from app.models_db import Encounter

router = APIRouter(prefix="/encounters", tags=["answers"])


@router.get("/{encounter_id}/next-step")
def get_next_step(
    encounter: Encounter = Depends(get_encounter_for_path),
    session: Session = Depends(get_session),
) -> dict:
    return serialize_next_step(compute_next_step(session, encounter))


@router.post("/{encounter_id}/answer")
def post_answer(
    body: AnswerRequest,
    encounter: Encounter = Depends(get_encounter_for_path),
    session: Session = Depends(get_session),
) -> dict:
    submit_answer(session, encounter, body.field_path, body.value)
    session.refresh(encounter)
    return serialize_next_step(compute_next_step(session, encounter))
