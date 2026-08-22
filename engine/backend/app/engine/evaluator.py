"""
The protocol engine's core: walks a ProtocolDefinition's blocks in order
against the current namespace + raw answers, and produces either the next
askable "frontier" (a set of fields, not one question at a time -- this is
what lets parallel tracks render at equal visual weight) or a terminal
resolution.

Pure function of (protocol definition, current answers) -- no caching, no
persisted derived values. Called fresh on every read; recomputation is cheap
at this scale and this sidesteps an entire class of cache-invalidation bugs.

No protocol-specific field name appears anywhere in this file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.engine.expr import MISSING, evaluate, get_var, is_determinable
from app.engine.namespace import set_var
from app.models_protocol import (
    ContextBlock,
    DerivedTagsBlock,
    DrugRecommendationBlock,
    FieldDef,
    GateBlock,
    ProtocolDefinition,
    TerminalTableBlock,
    TrackDef,
    TrackGroupBlock,
)

TriState = Literal["answered", "skipped_by_rule", "not_reached"]


@dataclass
class FrontierField:
    protocol_id: str
    block_id: str
    track_id: str | None
    field: FieldDef
    answer_path: str  # where a POSTed answer for this field should be written
    suggested_value: Any = None  # from field.prefill, if determinable yet -- a hint only, never auto-answered


@dataclass
class AnsweredField(FrontierField):
    """A field this encounter already holds an answer for.

    The frontier says what is still outstanding; this says what is settled.
    Both are produced by the same walk, from the same path arithmetic, on
    purpose -- a second function that recomputed answer paths independently
    would drift from this one the first time a block type changed, and the
    client would start posting corrections to paths that no longer exist.
    """

    value: Any = None


@dataclass
class TrackEvidence:
    track_id: str
    label: str
    mode: str
    resolution: str | None  # e.g. "typical" / "positive" / None if not yet resolved
    per_field: dict[str, dict[str, Any]]  # field_id -> {"status": ..., "value": ...}
    positive_count: int = 0
    negative_count: int = 0
    unknown_count: int = 0
    skipped_count: int = 0
    total_scored_fields: int = 0


@dataclass
class ProtocolEvalResult:
    protocol_id: str
    status: Literal["active", "resolved"]
    frontier: list[FrontierField] = field(default_factory=list)
    terminal: dict[str, str] | None = None  # {"code": ..., "headline": ...}
    tracks: list[TrackEvidence] = field(default_factory=list)
    unassessed: list[dict[str, str]] = field(default_factory=list)  # [{"field_id","label","reason"}]
    derived_tags: list[dict[str, Any]] = field(default_factory=list)  # [{"id","label","value"}]
    context_blocks: list[dict[str, Any]] = field(default_factory=list)
    drug_blocks: list[dict[str, Any]] = field(default_factory=list)
    answered: list[AnsweredField] = field(default_factory=list)


def _field_path(protocol_id: str, *segments: str) -> str:
    return ".".join(("protocols", protocol_id, *segments))


def _compute_prefill(field_def: FieldDef, namespace: dict) -> Any:
    """A prefill is a UI hint only -- it never auto-answers a field, it just
    suggests a starting value the doctor can accept or override."""
    prefill = field_def.prefill
    if prefill is None:
        return None
    source_value = get_var(namespace, prefill.source_path)
    if source_value is MISSING:
        return prefill.default
    mapped = prefill.value_map.get(str(source_value))
    return mapped if mapped is not None else prefill.default


def _resolve_field_state(
    field_def: FieldDef,
    namespace: dict,
    answered: bool,
    value: Any,
) -> tuple[TriState, Any]:
    """A field is answered / skipped-by-rule / not-yet-reachable, regardless
    of whether its answer would come from this protocol's own raw_answers or
    from the shared clinical-history store -- the caller resolves `answered`/
    `value` from whichever source applies and this function does the rest.
    Determining 'skipped' requires the fields its skip_when references to be
    answered first -- if they aren't yet, the field is left pending (neither
    frontier nor skipped), never guessed at."""
    if answered:
        return "answered", value
    if field_def.skip_when is not None and is_determinable(field_def.skip_when, namespace):
        if evaluate(field_def.skip_when, namespace):
            return "skipped_by_rule", None
    return "not_reached", None


def _compute_axis_count_resolution(track: TrackDef, per_field: dict[str, dict[str, Any]]) -> tuple[str | None, int, int, int]:
    positive = negative = unknown = 0
    for f in track.fields:
        status = per_field[f.id]["status"]
        if status == "skipped":
            continue
        axis = f.value_scoring.get(per_field[f.id]["value"], "unknown")
        per_field[f.id]["status"] = axis
        if axis == "positive":
            positive += 1
        elif axis in ("negative", "partial_negative"):
            negative += 1
        else:
            unknown += 1
    label = None
    assert track.resolution_rule is not None
    for threshold in track.resolution_rule.thresholds:
        if positive >= threshold.min_positive:
            label = threshold.label
            break
    return label, positive, negative, unknown


def _compute_any_true_resolution(track: TrackDef, per_field: dict[str, dict[str, Any]]) -> str:
    any_true = False
    for f in track.fields:
        entry = per_field[f.id]
        if entry["status"] == "skipped":
            continue
        if entry["value"] is True:
            any_true = True
            entry["status"] = "true"
        else:
            entry["status"] = "false"
    return "positive" if any_true else "negative"


def _compute_numeric_thresholds_resolution(track: TrackDef, namespace: dict) -> str | None:
    for t in track.numeric_thresholds:
        if is_determinable(t.when, namespace) and evaluate(t.when, namespace):
            return t.label
    return None


def _compute_decision_table_resolution(track: TrackDef, namespace: dict) -> str | None:
    """Same first-match-wins row logic as a protocol's terminal_table, scoped
    to one track. Rows may reference shared.* fields directly (not just this
    track's own `fields`) -- e.g. the valve-assessment decision (DOAC / VKA /
    blocked) that Module F and Module R both consult."""
    for row in track.decision_rows:
        if is_determinable(row.when, namespace) and evaluate(row.when, namespace):
            return row.label
    return None


def _process_gate_block(
    block: GateBlock,
    namespace: dict,
    protocol_id: str,
    raw_answers: dict[str, Any],
    answered: list[AnsweredField],
) -> tuple[list[FrontierField], bool, dict[str, str] | None]:
    frontier: list[FrontierField] = []
    for f in block.fields:
        path = _field_path(protocol_id, block.id, f.id)
        if path in raw_answers:
            set_var(namespace, path, raw_answers[path])
            answered.append(AnsweredField(protocol_id, block.id, None, f, path, value=raw_answers[path]))
        else:
            frontier.append(FrontierField(protocol_id, block.id, None, f, path))
    if frontier:
        return frontier, False, None
    if evaluate(block.fire_when, namespace):
        return [], True, {"code": block.terminal_code, "headline": block.terminal_headline}
    return [], True, None


def _process_derived_tags_block(block: DerivedTagsBlock, namespace: dict, protocol_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tag in block.tags:
        value: bool | None = None
        if is_determinable(tag.condition, namespace):
            value = bool(evaluate(tag.condition, namespace))
            set_var(namespace, _field_path(protocol_id, block.id, tag.id), value)
        out.append({"id": tag.id, "label": tag.label, "value": value})
    return out


def _process_track_group_block(
    block: TrackGroupBlock,
    namespace: dict,
    protocol_id: str,
    raw_answers: dict[str, Any],
    shared_answers: dict[str, Any],
    answered: list[AnsweredField],
) -> tuple[list[FrontierField], bool, list[TrackEvidence], list[dict[str, str]]]:
    frontier: list[FrontierField] = []
    complete = True
    evidences: list[TrackEvidence] = []
    unassessed: list[dict[str, str]] = []

    for track in block.tracks:
        per_field: dict[str, dict[str, Any]] = {}
        all_fields = list(track.fields) + list(track.display_fields)
        for f in all_fields:
            path = _field_path(protocol_id, "tracks", track.id, f.id)

            if f.source == "shared":
                assert f.shared_path is not None
                is_answered = f.shared_path in shared_answers
                raw_value = shared_answers.get(f.shared_path)
                answer_path = f"shared.{f.shared_path}"
            else:
                is_answered = path in raw_answers
                raw_value = raw_answers.get(path)
                answer_path = path

            state, value = _resolve_field_state(f, namespace, is_answered, raw_value)
            if state == "answered":
                set_var(namespace, path, value)
                per_field[f.id] = {"status": "answered", "value": value}
                answered.append(AnsweredField(protocol_id, block.id, track.id, f, answer_path, value=raw_value))
            elif state == "skipped_by_rule":
                per_field[f.id] = {"status": "skipped", "value": None}
                unassessed.append({"field_id": f.id, "label": f.label, "reason": "skipped_by_rule"})
            else:
                complete = False
                frontier.append(
                    FrontierField(protocol_id, block.id, track.id, f, answer_path, _compute_prefill(f, namespace))
                )

        scored_done = all(per_field.get(f.id, {}).get("status") in ("answered", "skipped") for f in track.fields)
        resolution_label: str | None = None
        positive = negative = unknown = 0
        if scored_done:
            if track.mode == "axis_count":
                resolution_label, positive, negative, unknown = _compute_axis_count_resolution(track, per_field)
            elif track.mode == "any_true":
                resolution_label = _compute_any_true_resolution(track, per_field)
            elif track.mode == "numeric_thresholds":
                resolution_label = _compute_numeric_thresholds_resolution(track, namespace)
            elif track.mode == "decision_table":
                resolution_label = _compute_decision_table_resolution(track, namespace)
            elif track.mode == "single_choice":
                # Exactly one field, whose answered value (or None if it was
                # skipped) *is* the track's resolution -- no scoring, just a
                # categorical decision point, generically supported so any
                # protocol can use it, not just AF's rhythm-control substrate.
                only_field = track.fields[0]
                entry = per_field.get(only_field.id, {})
                resolution_label = entry.get("value") if entry.get("status") == "answered" else None
                if resolution_label is not None:
                    entry["status"] = "answered"
            elif track.mode == "checklist_score":
                true_count = sum(
                    1 for f in track.fields
                    if per_field.get(f.id, {}).get("status") == "answered" and per_field[f.id]["value"] is True
                )
                positive = true_count
                resolution_label = f"{true_count} of {len(track.fields)} factors present"
                for f in track.fields:
                    per_field[f.id]["status"] = "true" if per_field[f.id].get("value") is True else (
                        "skipped" if per_field[f.id]["status"] == "skipped" else "false"
                    )
            if resolution_label is not None:
                set_var(namespace, _field_path(protocol_id, "tracks", track.id, "resolution"), resolution_label)

        evidences.append(
            TrackEvidence(
                track_id=track.id,
                label=track.label,
                mode=track.mode,
                resolution=resolution_label,
                per_field=per_field,
                positive_count=positive,
                negative_count=negative,
                unknown_count=unknown,
                skipped_count=sum(1 for f in track.fields if per_field.get(f.id, {}).get("status") == "skipped"),
                total_scored_fields=len(track.fields),
            )
        )

    return frontier, complete, evidences, unassessed


def _process_context_block(
    block: ContextBlock,
    namespace: dict,
    protocol_id: str,
    raw_answers: dict[str, Any],
    shared_answers: dict[str, Any],
    answered: list[AnsweredField],
) -> tuple[list[FrontierField], bool, dict[str, Any]]:
    frontier: list[FrontierField] = []
    complete = True
    values: dict[str, Any] = {}
    for f in block.fields:
        path = _field_path(protocol_id, block.id, f.id)
        if f.source == "shared":
            assert f.shared_path is not None
            is_answered = f.shared_path in shared_answers
            raw_value = shared_answers.get(f.shared_path)
            answer_path = f"shared.{f.shared_path}"
        else:
            is_answered = path in raw_answers
            raw_value = raw_answers.get(path)
            answer_path = path

        state, value = _resolve_field_state(f, namespace, is_answered, raw_value)
        if state == "answered":
            set_var(namespace, path, value)
            values[f.id] = value
            answered.append(AnsweredField(protocol_id, block.id, None, f, answer_path, value=raw_value))
        elif state == "skipped_by_rule":
            pass  # optional-style skip: simply absent from `values`, not an error
        elif f.required:
            frontier.append(FrontierField(protocol_id, block.id, None, f, answer_path))
            complete = False
        # else: optional, unanswered, not skip-ruled -- leave out, don't block completion
    return frontier, complete, values


def _process_terminal_table_block(block: TerminalTableBlock, namespace: dict) -> dict[str, str] | None:
    for row in block.rows:
        if is_determinable(row.when, namespace) and evaluate(row.when, namespace):
            return {"code": row.code, "headline": row.headline}
    if block.default_code:
        return {"code": block.default_code, "headline": block.default_headline or ""}
    return None


def _process_drug_recommendation_block(
    block: DrugRecommendationBlock, namespace: dict, protocol_id: str
) -> dict[str, Any]:
    """Never contributes to the frontier -- there is nothing to ask here, only
    to compute and display, once its inputs (typically a terminal code from an
    earlier block) are known."""
    if block.applicable_when is not None:
        if not is_determinable(block.applicable_when, namespace):
            return {"id": block.id, "label": block.label, "status": "pending", "entries": [], "hidden_count": 0}
        if not evaluate(block.applicable_when, namespace):
            return {"id": block.id, "label": block.label, "status": "not_applicable", "entries": [], "hidden_count": 0}

    tier = get_var(namespace, block.facility_tier_path)
    entries_out: list[dict[str, Any]] = []
    hidden_count = 0

    for entry in block.entries:
        if tier is not MISSING and entry.tiers and tier not in entry.tiers:
            hidden_count += 1
            continue
        if entry.applicable_when is not None:
            if not is_determinable(entry.applicable_when, namespace):
                continue
            if not evaluate(entry.applicable_when, namespace):
                continue  # doesn't apply to this route/terminal -- simply absent, not "blocked"

        if entry.quarantine_reason:
            entries_out.append(
                {
                    "id": entry.id,
                    "name": entry.name,
                    "dose": entry.dose,
                    "group_label": entry.group_label,
                    "state": "quarantined",
                    "block_reasons": [{"reason": entry.quarantine_reason, "vitalis_addition": True}],
                    "caution_reasons": [],
                    "note": entry.note,
                }
            )
            continue

        block_reasons = []
        caution_reasons = []
        for il in entry.interlocks:
            if is_determinable(il.condition, namespace) and evaluate(il.condition, namespace):
                target = block_reasons if il.state == "block" else caution_reasons
                target.append({"reason": il.reason, "vitalis_addition": il.vitalis_addition})

        state = "block" if block_reasons else ("caution" if caution_reasons else "clear")
        entries_out.append(
            {
                "id": entry.id,
                "name": entry.name,
                "dose": entry.dose,
                "group_label": entry.group_label,
                "state": state,
                "block_reasons": block_reasons,
                "caution_reasons": caution_reasons,
                "note": entry.note,
            }
        )

    return {"id": block.id, "label": block.label, "status": "ready", "entries": entries_out, "hidden_count": hidden_count}


def evaluate_protocol(
    protocol: ProtocolDefinition,
    namespace: dict,
    raw_answers: dict[str, Any],
    shared_answers: dict[str, Any],
) -> ProtocolEvalResult:
    pid = protocol.id
    namespace.setdefault("protocols", {}).setdefault(pid, {})
    tracks: list[TrackEvidence] = []
    unassessed: list[dict[str, str]] = []
    derived_tags: list[dict[str, Any]] = []
    context_blocks: list[dict[str, Any]] = []
    drug_blocks: list[dict[str, Any]] = []
    terminal: dict[str, str] | None = None

    answered: list[AnsweredField] = []

    def snapshot(status: Literal["active", "resolved"], frontier: list[FrontierField]) -> ProtocolEvalResult:
        return ProtocolEvalResult(
            pid, status, frontier, terminal, tracks, unassessed, derived_tags, context_blocks, drug_blocks,
            answered,
        )

    for block in protocol.blocks:
        if isinstance(block, GateBlock):
            frontier, complete, gate_terminal = _process_gate_block(block, namespace, pid, raw_answers, answered)
            if not complete:
                return snapshot("active", frontier)
            if gate_terminal:
                # A gate terminal is a hard stop (e.g. ACS suspected) -- session
                # ends here, nothing after it (including any drug workup) runs.
                terminal = gate_terminal
                return snapshot("resolved", [])
            continue

        if isinstance(block, DerivedTagsBlock):
            derived_tags.extend(_process_derived_tags_block(block, namespace, pid))
            continue

        if isinstance(block, TrackGroupBlock):
            frontier, complete, evidences, block_unassessed = _process_track_group_block(
                block, namespace, pid, raw_answers, shared_answers, answered
            )
            tracks.extend(evidences)
            unassessed.extend(block_unassessed)
            if not complete:
                return snapshot("active", frontier)
            continue

        if isinstance(block, ContextBlock):
            frontier, complete, values = _process_context_block(
                block, namespace, pid, raw_answers, shared_answers, answered
            )
            context_blocks.append(
                {"id": block.id, "label": block.label, "render_hint": block.render_hint, "fields": values}
            )
            if not complete:
                return snapshot("active", frontier)
            continue

        if isinstance(block, TerminalTableBlock):
            # Unlike a gate, resolving here does NOT stop the walk -- later
            # blocks (potentiating factors, drug proposals) may depend on
            # knowing the terminal code, so they still need to run.
            resolved = _process_terminal_table_block(block, namespace)
            if resolved is not None:
                set_var(namespace, _field_path(pid, block.id, "code"), resolved["code"])
                terminal = resolved
            continue

        if isinstance(block, DrugRecommendationBlock):
            drug_blocks.append(_process_drug_recommendation_block(block, namespace, pid))
            continue

    return snapshot("resolved" if terminal is not None else "active", [])
