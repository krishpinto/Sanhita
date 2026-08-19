from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.auth import get_encounter_for_path
from app.db import get_session
from app.engine_service import PROTOCOLS, activate_protocol, compute_next_step, serialize_next_step
from app.models_db import Encounter

router = APIRouter(tags=["protocols"])


@router.get("/protocols")
def list_protocols() -> list[dict]:
    return [
        {
            "protocol_id": p.id,
            "name": p.name,
            "version": p.version,
            "fidelity": p.fidelity,
            "fidelity_note": p.fidelity_note,
            "source_citation": p.source_citation,
            "has_auto_trigger": p.activation.auto_trigger is not None,
            "has_offer_trigger": p.activation.offer_trigger is not None,
        }
        for p in PROTOCOLS.values()
    ]


@router.post("/encounters/{encounter_id}/activate-protocol/{protocol_id}")
def post_activate_protocol(
    protocol_id: str,
    encounter: Encounter = Depends(get_encounter_for_path),
    session: Session = Depends(get_session),
) -> dict:
    activate_protocol(session, encounter, protocol_id)
    return serialize_next_step(compute_next_step(session, encounter))
