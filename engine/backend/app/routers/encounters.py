import json

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.auth import get_encounter_for_path, new_access_token
from app.db import get_session
from app.models_api import EncounterCreateResponse
from app.models_db import Encounter

router = APIRouter(prefix="/encounters", tags=["encounters"])


@router.post("", response_model=EncounterCreateResponse)
def create_encounter(session: Session = Depends(get_session)) -> EncounterCreateResponse:
    encounter = Encounter(access_token=new_access_token())
    session.add(encounter)
    session.commit()
    session.refresh(encounter)
    return EncounterCreateResponse(encounter_id=encounter.id, access_token=encounter.access_token)


@router.get("/{encounter_id}")
def get_encounter_summary(
    encounter: Encounter = Depends(get_encounter_for_path),
) -> dict:
    return {
        "id": encounter.id,
        "status": encounter.status,
        "created_at": encounter.created_at.isoformat(),
        "updated_at": encounter.updated_at.isoformat(),
        "patient_name": encounter.patient_name,
        "patient_age": encounter.patient_age,
        "patient_sex": encounter.patient_sex,
        "symptoms": json.loads(encounter.symptoms_json) if encounter.symptoms_json else [],
        "facility_tier": encounter.facility_tier,
        "core_terminal_code": encounter.core_terminal_code,
        "core_terminal_headline": encounter.core_terminal_headline,
    }
