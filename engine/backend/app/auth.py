"""Bearer-token-per-encounter auth. No cookies, no user accounts -- deliberately
minimal so a future React Native/Expo client authenticates exactly the way the
web demo does: hold the token, send it as a header."""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select

from app.db import get_session
from app.models_db import Encounter

_bearer = HTTPBearer(auto_error=False)


def new_access_token() -> str:
    return secrets.token_urlsafe(32)


def get_current_encounter(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> Encounter:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    encounter = session.exec(
        select(Encounter).where(Encounter.access_token == credentials.credentials)
    ).first()
    if encounter is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired access token")
    return encounter


def get_encounter_for_path(
    encounter_id: str,
    encounter: Encounter = Depends(get_current_encounter),
) -> Encounter:
    """Bearer token already fully identifies the encounter; this just checks
    the path id matches it, so a client that mixed up two encounter ids gets
    a clear 404 instead of silently operating on the wrong one."""
    if encounter.id != encounter_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Encounter not found")
    return encounter
