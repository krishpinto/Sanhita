from typing import Any

from pydantic import BaseModel


class EncounterCreateResponse(BaseModel):
    encounter_id: str
    access_token: str


class AnswerRequest(BaseModel):
    field_path: str
    value: Any = None


class DoctorOpinionRequest(BaseModel):
    doctor_note: str | None = None
    structured_alternate_diagnosis: str | None = None


class AiOpinionRequestOptions(BaseModel):
    force_refresh: bool = False
