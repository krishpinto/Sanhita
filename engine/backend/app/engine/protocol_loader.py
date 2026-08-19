"""Loads and validates every protocols/*.json file into ProtocolDefinition
objects at startup. A malformed protocol file fails loudly here rather than
surfacing as a confusing runtime error mid-encounter."""

from __future__ import annotations

import json
from pathlib import Path

from app.models_protocol import ProtocolDefinition

DEFAULT_PROTOCOLS_DIR = Path(__file__).resolve().parent.parent.parent / "protocols"


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
        protocols[protocol.id] = protocol
    return protocols
