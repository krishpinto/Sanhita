"""Wires the pure engine (app.engine.*) to SQLite. This is the one place that
knows about both the DB and the protocol engine -- app.engine.* itself stays
completely DB-agnostic and unit-testable without a database.

The engine is re-run from scratch (fresh namespace, fresh raw answers pulled
from the DB) on every call. No derived value is ever cached across requests.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core_intake import CORE_STEPS, check_st_elevation_hard_exit, project_ecg_finding
from app.differential_engine import (
    build_confirmation_field,
    build_findings_field,
    compute_differential,
    pending_confirmation_ids,
    raised_item_ids,
)
from app.engine.evaluator import FrontierField, ProtocolEvalResult, evaluate_protocol
from app.engine.expr import evaluate as expr_evaluate
from app.engine.expr import is_determinable
from app.engine.namespace import build_base_namespace
from app.engine.protocol_loader import load_protocols
from app.models_db import Answer, Encounter, ProtocolActivation, SharedClinicalHistoryEntry
from app.models_protocol import ProtocolDefinition
from app.shared_fields import RISK_FACTOR_FIELDS

PROTOCOLS: dict[str, ProtocolDefinition] = load_protocols()


@dataclass
class NextStepResult:
    core_frontier: list[FrontierField]
    core_terminal: dict[str, str] | None
    offered_protocols: list[dict[str, str]]
    active_protocols: list[ProtocolEvalResult]
    ready_for_result: bool


def _core_answers(encounter: Encounter) -> dict[str, Any]:
    answers: dict[str, Any] = {}
    if encounter.facility_tier is not None:
        answers["facility_tier"] = encounter.facility_tier
    if encounter.patient_name is not None:
        answers["name"] = encounter.patient_name
    if encounter.patient_age is not None:
        answers["age"] = encounter.patient_age
    if encounter.patient_sex is not None:
        answers["sex"] = encounter.patient_sex
    if encounter.symptoms_json is not None:
        answers["symptoms"] = json.loads(encounter.symptoms_json)
    if encounter.differential_answers_json is not None:
        answers["differential_answers"] = json.loads(encounter.differential_answers_json)
    if encounter.differential_confirmations_json is not None:
        answers["differential_confirmations"] = json.loads(encounter.differential_confirmations_json)
    if encounter.ecg_json is not None:
        answers["ecg"] = json.loads(encounter.ecg_json)
    if encounter.vitals_json is not None:
        answers["vitals"] = json.loads(encounter.vitals_json)
    return answers


def _core_namespace_projection(core_answers: dict[str, Any]) -> dict[str, Any]:
    projected = dict(core_answers)
    if "ecg" in projected and projected["ecg"] is not None:
        projected["ecg"] = project_ecg_finding(projected["ecg"])
    if "symptoms" in projected:
        result = compute_differential(
            projected["symptoms"],
            projected.get("differential_answers"),
            projected.get("differential_confirmations"),
        )
        projected["differential"] = {"surviving_modules": sorted(result.surviving_modules)}
    return projected


def _core_step(step_id: str):
    return next(s for s in CORE_STEPS if s.id == step_id)


def get_core_frontier(
    session: Session, encounter: Encounter
) -> tuple[list[FrontierField], dict[str, str] | None]:
    core_answers = _core_answers(encounter)
    shared_answers = _shared_answers(session, encounter.id)

    # 1-2: facility tier, patient details -- fixed, JSON-defined steps
    for step_id in ("facility_tier_step", "patient_details"):
        step = _core_step(step_id)
        unanswered = [f for f in step.fields if f.id not in core_answers]
        if unanswered:
            return [FrontierField("core", step.id, None, f, f"core.{f.id}") for f in unanswered], None

    # 3: shared patient core risk factors -- asked once, upfront, answers land in
    # the shared store so every module that needs one reads the same value.
    unanswered_shared = [f for f in RISK_FACTOR_FIELDS if f.id not in shared_answers]
    if unanswered_shared:
        return [
            FrontierField("core", "risk_factors_step", None, f, f"shared.{f.id}") for f in unanswered_shared
        ], None

    # 4: symptoms -- multi-select, "never just one chief complaint"
    symptoms_step = _core_step("symptoms_step")
    unanswered = [f for f in symptoms_step.fields if f.id not in core_answers]
    if unanswered:
        return [FrontierField("core", symptoms_step.id, None, f, f"core.{f.id}") for f in unanswered], None

    # 5: differential engine -- symptoms in, tiered differential out; each
    # item is resolved by one bedside discriminator question, not clinician
    # judgement. Skipped entirely (not asked, not required) if the symptom
    # set raised nothing to review.
    symptoms = core_answers.get("symptoms", [])
    if raised_item_ids(symptoms) and "differential_answers" not in core_answers:
        field = build_findings_field(symptoms)
        return [
            FrontierField("core", "differential_review_step", None, field, "core.differential_answers")
        ], None

    # 5b: Rule 2 -- the killers never auto-exclude. Any tier-1 item whose
    # discriminator came back negative is parked, and dropping it takes one
    # deliberate tap here. Observing a finding and excluding a diagnosis are
    # kept as two separate acts on purpose: that separation is the safety
    # property, not a UI nicety. Skipped when nothing is awaiting a decision.
    if (
        "differential_answers" in core_answers
        and pending_confirmation_ids(symptoms, core_answers.get("differential_answers"))
        and "differential_confirmations" not in core_answers
    ):
        field = build_confirmation_field(symptoms, core_answers.get("differential_answers"))
        return [
            FrontierField("core", "differential_confirmation_step", None, field, "core.differential_confirmations")
        ], None

    # 6: ECG -- shared investigation, all findings always shown; then the
    # ST-elevation hard exit, which the differential's Tier-1 "aortic
    # dissection / ACS / PE / pneumothorax / severe AS" list deliberately
    # does not replace -- those stay listed as still-open, this is a harder,
    # blocking stop.
    ecg_step = _core_step("ecg_step")
    unanswered = [f for f in ecg_step.fields if f.id not in core_answers]
    if unanswered:
        return [FrontierField("core", ecg_step.id, None, f, f"core.{f.id}") for f in unanswered], None
    terminal = check_st_elevation_hard_exit(core_answers["ecg"])
    if terminal:
        return [], terminal

    # 7: vitals -- optional
    vitals_step = _core_step("vitals_step")
    unanswered = [f for f in vitals_step.fields if f.id not in core_answers]
    if unanswered:
        return [FrontierField("core", vitals_step.id, None, f, f"core.{f.id}") for f in unanswered], None

    return [], None


def _shared_answers(session: Session, encounter_id: str) -> dict[str, Any]:
    rows = session.exec(
        select(SharedClinicalHistoryEntry).where(SharedClinicalHistoryEntry.encounter_id == encounter_id)
    ).all()
    return {row.field_id: json.loads(row.value_json) for row in rows}


def _activations(session: Session, encounter_id: str) -> dict[str, ProtocolActivation]:
    rows = session.exec(select(ProtocolActivation).where(ProtocolActivation.encounter_id == encounter_id)).all()
    return {row.protocol_id: row for row in rows}


def _raw_answers_for_activation(session: Session, activation_id: int) -> dict[str, Any]:
    rows = session.exec(select(Answer).where(Answer.protocol_activation_id == activation_id)).all()
    return {row.field_path: json.loads(row.raw_value_json) for row in rows}


def compute_next_step(session: Session, encounter: Encounter) -> NextStepResult:
    core_frontier, core_terminal = get_core_frontier(session, encounter)
    if core_terminal:
        if encounter.core_terminal_code != core_terminal["code"]:
            encounter.core_terminal_code = core_terminal["code"]
            encounter.core_terminal_headline = core_terminal["headline"]
            encounter.status = "completed"
            encounter.updated_at = datetime.now(timezone.utc)
            session.add(encounter)
            session.commit()
        return NextStepResult([], core_terminal, [], [], False)
    if core_frontier:
        return NextStepResult(core_frontier, None, [], [], False)

    core = _core_namespace_projection(_core_answers(encounter))
    shared = _shared_answers(session, encounter.id)
    namespace = build_base_namespace(core, shared)

    activations = _activations(session, encounter.id)
    offered: list[dict[str, str]] = []
    active_results: list[ProtocolEvalResult] = []
    any_pending = False

    for pid, protocol in PROTOCOLS.items():
        activation = activations.get(pid)
        if activation is None:
            auto_trigger = protocol.activation.auto_trigger
            offer_trigger = protocol.activation.offer_trigger
            auto_fires = (
                auto_trigger is not None
                and is_determinable(auto_trigger, namespace)
                and expr_evaluate(auto_trigger, namespace)
            )
            if auto_fires:
                activation = ProtocolActivation(
                    encounter_id=encounter.id,
                    protocol_id=pid,
                    protocol_version=protocol.version,
                    activation_mode="auto",
                    status="active",
                )
                session.add(activation)
                session.commit()
                session.refresh(activation)
                activations[pid] = activation
            else:
                offer_fires = (
                    offer_trigger is not None
                    and is_determinable(offer_trigger, namespace)
                    and expr_evaluate(offer_trigger, namespace)
                )
                if offer_fires:
                    offered.append(
                        {
                            "protocol_id": pid,
                            "name": protocol.name,
                            "fidelity": protocol.fidelity,
                            "fidelity_note": protocol.fidelity_note or "",
                        }
                    )
                continue

        raw_answers = _raw_answers_for_activation(session, activation.id)
        result = evaluate_protocol(protocol, namespace, raw_answers, shared)
        active_results.append(result)

        if result.status == "resolved" and activation.status != "resolved":
            activation.status = "resolved"
            activation.terminal_code = result.terminal["code"] if result.terminal else None
            activation.terminal_headline = result.terminal["headline"] if result.terminal else None
            session.add(activation)
            session.commit()
        elif result.status == "active":
            any_pending = True

    ready_for_result = (not any_pending) and any(r.status == "resolved" for r in active_results)
    if ready_for_result and encounter.status != "completed":
        encounter.status = "completed"
        encounter.updated_at = datetime.now(timezone.utc)
        session.add(encounter)
        session.commit()
    elif not ready_for_result and encounter.status == "intake":
        encounter.status = "in_progress"
        encounter.updated_at = datetime.now(timezone.utc)
        session.add(encounter)
        session.commit()

    return NextStepResult(core_frontier, None, offered, active_results, ready_for_result)


def all_frontier_paths(result: NextStepResult) -> set[str]:
    paths = {f.answer_path for f in result.core_frontier}
    for r in result.active_protocols:
        paths |= {f.answer_path for f in r.frontier}
    return paths


def activate_protocol(session: Session, encounter: Encounter, protocol_id: str) -> ProtocolActivation:
    if protocol_id not in PROTOCOLS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown protocol '{protocol_id}'")
    existing = session.exec(
        select(ProtocolActivation).where(
            ProtocolActivation.encounter_id == encounter.id, ProtocolActivation.protocol_id == protocol_id
        )
    ).first()
    if existing:
        return existing
    protocol = PROTOCOLS[protocol_id]
    activation = ProtocolActivation(
        encounter_id=encounter.id,
        protocol_id=protocol_id,
        protocol_version=protocol.version,
        activation_mode="offered_accepted",
        status="active",
    )
    session.add(activation)
    session.commit()
    session.refresh(activation)
    return activation


def submit_answer(session: Session, encounter: Encounter, field_path: str, value: Any) -> None:
    current = compute_next_step(session, encounter)
    if field_path not in all_frontier_paths(current):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Field '{field_path}' is not currently answerable (stale client state, or already answered).",
        )

    if field_path.startswith("core."):
        key = field_path.split(".", 1)[1]
        if key == "facility_tier":
            encounter.facility_tier = value
        elif key == "name":
            encounter.patient_name = value
        elif key == "age":
            encounter.patient_age = value
        elif key == "sex":
            encounter.patient_sex = value
        elif key == "symptoms":
            encounter.symptoms_json = json.dumps(value)
        elif key == "differential_answers":
            encounter.differential_answers_json = json.dumps(value)
        elif key == "differential_confirmations":
            encounter.differential_confirmations_json = json.dumps(value)
        elif key == "ecg":
            encounter.ecg_json = json.dumps(value)
        elif key == "vitals":
            encounter.vitals_json = json.dumps(value)
        else:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown core field '{key}'")
        encounter.updated_at = datetime.now(timezone.utc)
        session.add(encounter)
        session.commit()
        return

    if field_path.startswith("shared."):
        field_id = field_path.split(".", 1)[1]
        existing = session.exec(
            select(SharedClinicalHistoryEntry).where(
                SharedClinicalHistoryEntry.encounter_id == encounter.id,
                SharedClinicalHistoryEntry.field_id == field_id,
            )
        ).first()
        if existing:
            existing.value_json = json.dumps(value)
            existing.answered_at = datetime.now(timezone.utc)
            session.add(existing)
        else:
            session.add(
                SharedClinicalHistoryEntry(encounter_id=encounter.id, field_id=field_id, value_json=json.dumps(value))
            )
        session.commit()
        return

    if field_path.startswith("protocols."):
        protocol_id = field_path.split(".")[1]
        activation = session.exec(
            select(ProtocolActivation).where(
                ProtocolActivation.encounter_id == encounter.id,
                ProtocolActivation.protocol_id == protocol_id,
                ProtocolActivation.status == "active",
            )
        ).first()
        if activation is None:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Protocol '{protocol_id}' is not active for this encounter")
        existing_answer = session.exec(
            select(Answer).where(
                Answer.protocol_activation_id == activation.id, Answer.field_path == field_path
            )
        ).first()
        if existing_answer:
            existing_answer.raw_value_json = json.dumps(value)
            session.add(existing_answer)
        else:
            session.add(Answer(protocol_activation_id=activation.id, field_path=field_path, raw_value_json=json.dumps(value)))
        session.commit()
        return

    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unrecognized field path '{field_path}'")


# ---------- serialization ----------


def serialize_field(f) -> dict[str, Any]:  # FieldDef
    return f.model_dump(exclude_none=False)


def _lookup_labels(protocol_id: str, block_id: str, track_id: str | None) -> tuple[str, str | None, str | None, str | None]:
    """Returns (block_label, track_label, block_description, track_description)."""
    if protocol_id == "core":
        if block_id == "risk_factors_step":
            return "Risk factors", None, "Collected once, upfront -- every module reads the same answers.", None
        if block_id == "differential_review_step":
            return (
                "The differential, and what settles it",
                None,
                "What the symptoms raise, worst-first -- then a handful of observations that "
                "resolve several of them at a time. You report findings; the system does the "
                "ruling out.",
                None,
            )
        if block_id == "differential_confirmation_step":
            return (
                "Confirm before dropping these",
                None,
                "Tier 1 never leaves the list on an examination finding alone.",
                None,
            )
        for step in CORE_STEPS:
            if step.id == block_id:
                return step.label, None, step.description, None
        return block_id.replace("_", " ").title(), None, None, None
    protocol = PROTOCOLS.get(protocol_id)
    if protocol is None:
        return block_id, track_id, None, None
    for block in protocol.blocks:
        if block.id != block_id:
            continue
        block_description = getattr(block, "description", None)
        if track_id is not None and hasattr(block, "tracks"):
            for track in block.tracks:  # type: ignore[attr-defined]
                if track.id == track_id:
                    return block.label, track.label, block_description, track.description
        return block.label, None, block_description, None
    return block_id, track_id, None, None


def serialize_frontier_field(ff: FrontierField) -> dict[str, Any]:
    block_label, track_label, block_description, track_description = _lookup_labels(
        ff.protocol_id, ff.block_id, ff.track_id
    )
    return {
        "protocol_id": ff.protocol_id,
        "block_id": ff.block_id,
        "block_label": block_label,
        "block_description": block_description,
        "track_id": ff.track_id,
        "track_label": track_label,
        "track_description": track_description,
        "answer_path": ff.answer_path,
        "field": serialize_field(ff.field),
        "suggested_value": ff.suggested_value,
    }


def serialize_protocol_result(r: ProtocolEvalResult) -> dict[str, Any]:
    return {
        "protocol_id": r.protocol_id,
        "status": r.status,
        "frontier": [serialize_frontier_field(f) for f in r.frontier],
        "terminal": r.terminal,
        "fidelity": PROTOCOLS[r.protocol_id].fidelity,
        "fidelity_note": PROTOCOLS[r.protocol_id].fidelity_note,
        "protocol_name": PROTOCOLS[r.protocol_id].name,
        "source_citation": PROTOCOLS[r.protocol_id].source_citation,
        "tracks": [
            {
                "track_id": t.track_id,
                "label": t.label,
                "mode": t.mode,
                "resolution": t.resolution,
                "positive_count": t.positive_count,
                "negative_count": t.negative_count,
                "unknown_count": t.unknown_count,
                "skipped_count": t.skipped_count,
                "total_scored_fields": t.total_scored_fields,
                "per_field": t.per_field,
            }
            for t in r.tracks
        ],
        "unassessed": r.unassessed,
        "derived_tags": r.derived_tags,
        "context_blocks": r.context_blocks,
        "drug_blocks": r.drug_blocks,
    }


def serialize_next_step(result: NextStepResult) -> dict[str, Any]:
    return {
        "core_frontier": [serialize_frontier_field(f) for f in result.core_frontier],
        "core_terminal": result.core_terminal,
        "offered_protocols": result.offered_protocols,
        "active_protocols": [serialize_protocol_result(r) for r in result.active_protocols],
        "ready_for_result": result.ready_for_result,
    }
