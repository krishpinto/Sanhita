"""Every consultation recorded so far, for review.

This is the one endpoint in the app that crosses encounters. Everything else
is scoped by a bearer token that identifies exactly one encounter and nothing
else -- so a caller who somehow gets a token can only ever see that patient.
This endpoint deliberately breaks that, which is why it is the only one with
a lock on it.

The lock is a single shared key (`ADMIN_KEY`), and that is not real
authentication -- it does not say who looked, it cannot be revoked for one
person, and everyone who reviews consultations shares it. It is here to stop
"anyone who has the URL can read every patient record", which is the state
the deployment would otherwise be in. Before real patient data goes in, this
needs actual accounts.
"""

from __future__ import annotations

import json
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, func, select

from app.config import settings
from app.db import get_session
from app.models_db import AnswerEvent, Encounter, ProtocolActivation

router = APIRouter(prefix="/consultations", tags=["history"])

_bearer = HTTPBearer(auto_error=False)


def require_admin(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> None:
    """Refuses rather than opens when unconfigured.

    A deployment that forgets to set ADMIN_KEY gets a disabled endpoint, not
    an unlocked one. The failure mode of the opposite default is every
    patient record readable by anyone who guesses the path.
    """
    if not settings.admin_key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Consultation history is not enabled on this deployment (ADMIN_KEY is not set).",
        )
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "This page needs the review key.")
    # Constant-time: a plain == leaks the key one character at a time to
    # anyone willing to time the responses.
    if not secrets.compare_digest(credentials.credentials, settings.admin_key):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "That review key is not right.")


@router.get("")
def list_consultations(
    session: Session = Depends(get_session),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(require_admin),
) -> dict[str, Any]:
    encounters = session.exec(
        select(Encounter).order_by(Encounter.created_at.desc()).limit(limit).offset(offset)
    ).all()
    total = session.exec(select(func.count()).select_from(Encounter)).one()

    ids = [e.id for e in encounters]
    # Three queries for the whole page, not three per row. A history page that
    # gets slower the more consultations it has is a history page nobody opens.
    outcomes = _outcomes_by_encounter(session, ids)
    counts = _question_counts_by_encounter(session, ids)

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "consultations": [
            {
                "id": e.id,
                # The review page opens a past consultation by holding its
                # token, exactly as the doctor's own browser did at the time.
                # Handing it out is only acceptable because this whole
                # endpoint is already behind the review key.
                "access_token": e.access_token,
                "created_at": e.created_at.isoformat(),
                "updated_at": e.updated_at.isoformat(),
                "status": e.status,
                "patient_name": e.patient_name,
                "patient_age": e.patient_age,
                "patient_sex": e.patient_sex,
                "facility_tier": e.facility_tier,
                "symptoms": json.loads(e.symptoms_json) if e.symptoms_json else [],
                "questions_answered": counts.get(e.id, 0),
                # A hard exit is an outcome, and the most important kind. An
                # encounter that stopped at ST elevation must not read as
                # "never finished".
                "safety_exit": e.core_terminal_headline,
                "outcomes": outcomes.get(e.id, []),
            }
            for e in encounters
        ],
    }


def _outcomes_by_encounter(session: Session, ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    """Read from the stored activations rather than re-running the engine.

    Re-evaluating every encounter to render one list would make this page cost
    a full engine walk per row, and the terminal was already written down when
    the protocol resolved.
    """
    if not ids:
        return {}
    rows = session.exec(
        select(ProtocolActivation).where(ProtocolActivation.encounter_id.in_(ids))
    ).all()
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.encounter_id, []).append(
            {
                "protocol_id": row.protocol_id,
                "status": row.status,
                "headline": row.terminal_headline,
            }
        )
    return grouped


def _question_counts_by_encounter(session: Session, ids: list[str]) -> dict[str, int]:
    if not ids:
        return {}
    rows = session.exec(
        select(AnswerEvent.encounter_id, func.count())
        .where(AnswerEvent.encounter_id.in_(ids))
        .group_by(AnswerEvent.encounter_id)
    ).all()
    return {encounter_id: count for encounter_id, count in rows}
