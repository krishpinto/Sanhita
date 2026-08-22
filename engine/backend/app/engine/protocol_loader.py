"""Loads and validates every protocols/*.json file into ProtocolDefinition
objects at startup. A malformed protocol file fails loudly here rather than
surfacing as a confusing runtime error mid-encounter."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from app.models_protocol import FieldDef, ProtocolDefinition
from app.shared_fields import SHARED_FIELDS

DEFAULT_PROTOCOLS_DIR = Path(__file__).resolve().parent.parent.parent / "protocols"

# Filled in from the shared registry when a protocol declares source="shared"
# but leaves them out. Anything the protocol states itself always wins.
_INHERITED_FROM_SHARED = ("options", "description", "input_source", "value_scoring")


def _walk_fields(node: object):
    """Yield every FieldDef anywhere in a protocol, however deeply nested."""
    if isinstance(node, FieldDef):
        yield node
        for sub in node.sub_fields:
            yield from _walk_fields(sub)
        return
    if isinstance(node, BaseModel):
        for name in type(node).model_fields:
            yield from _walk_fields(getattr(node, name))
        return
    if isinstance(node, (list, tuple)):
        for item in node:
            yield from _walk_fields(item)


def _resolve_shared_fields(protocol: ProtocolDefinition, path: Path) -> None:
    """Fill a shared field's blanks from the registry in app/shared_fields.py.

    A protocol that reads a shared field declares only what makes it specific
    -- its label and its skip_when. The answer set (`options`) belongs to the
    field itself, not to whichever module happens to ask first, so it lives in
    one place and is copied in here. Both RHD and AF shipped `echo_status`
    with no options at all, which rendered as a question with no answers and
    stranded the encounter; the guard below is what makes that a startup
    failure instead of a dead end mid-consultation.
    """
    for field in _walk_fields(protocol):
        if field.source == "shared":
            key = field.shared_path or field.id
            shared = SHARED_FIELDS.get(key)
            if shared is None:
                raise ValueError(
                    f"{path.name}: field '{field.id}' declares source='shared' with "
                    f"shared_path='{key}', which is not in SHARED_FIELDS. Add it to "
                    f"app/shared_fields.py, or declare the field locally."
                )
            for attr in _INHERITED_FROM_SHARED:
                mine, theirs = getattr(field, attr), getattr(shared, attr)
                if not mine and theirs:
                    setattr(field, attr, theirs)

        # A choice question with nothing to choose from cannot be answered, so
        # the encounter can never move past it. Never ship one.
        if field.field_type in ("single_select", "multi_select") and not field.options:
            raise ValueError(
                f"{path.name}: field '{field.id}' is a {field.field_type} with no "
                f"options -- it would render as an unanswerable question and strand "
                f"the encounter."
            )


def load_protocols(directory: Path | str = DEFAULT_PROTOCOLS_DIR) -> dict[str, ProtocolDefinition]:
    directory = Path(directory)
    protocols: dict[str, ProtocolDefinition] = {}
    for path in sorted(directory.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        try:
            protocol = ProtocolDefinition.model_validate(raw)
        except Exception as exc:  # noqa: BLE001 -- re-raise with file context, still fatal
            raise ValueError(f"Failed to load protocol file {path}: {exc}") from exc
        if protocol.id in protocols:
            raise ValueError(f"Duplicate protocol id '{protocol.id}' (from {path})")
        if protocol.id != path.stem:
            raise ValueError(
                f"Protocol id '{protocol.id}' in {path} does not match filename stem '{path.stem}'"
            )
        _resolve_shared_fields(protocol, path)
        protocols[protocol.id] = protocol
    return protocols
