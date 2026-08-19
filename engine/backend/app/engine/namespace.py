"""Namespace construction: turns the raw stored state of an encounter (core
intake answers, shared clinical-history answers, per-protocol raw answers)
into the nested dict that app.engine.expr evaluates `{"var": "a.b.c"}"`
references against.

The namespace is mutated in place as evaluator.py walks a protocol's blocks,
since later blocks (derived tags, track resolutions) inject computed values
that earlier blocks' expressions may reference. Nothing here is persisted --
the whole tree is rebuilt from raw answers on every read.
"""

from __future__ import annotations

from typing import Any


def set_var(namespace: dict, path: str, value: Any) -> None:
    """Nested-dict insertion by dotted path, creating intermediate dicts as
    needed. The mirror-image of app.engine.expr.get_var."""
    parts = path.split(".")
    cur = namespace
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def build_base_namespace(core: dict, shared: dict) -> dict:
    return {"core": core, "shared": shared, "protocols": {}}
