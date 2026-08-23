"""The AI 'second opinion' is pluggable and optional. It is built off the
same generic result payload every protocol produces (headlines, track
evidence, unassessed lists) -- never off protocol-specific field names, so a
new disease protocol doesn't require touching this file."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SecondOpinionContext:
    """The same encounter the doctor is looking at, in dict form.

    Every field here is one the result screen already renders. That is the
    point: a second opinion the doctor cannot trace back to what is on their
    own screen is not checkable, and an unshowable disagreement is worse than
    no second opinion at all.
    """

    core: dict[str, Any]
    protocols: list[dict[str, Any]]  # serialized protocol results (see engine_service.serialize_protocol_result)
    differential: dict[str, Any] | None = None
    unrun_protocols: list[dict[str, Any]] = field(default_factory=list)
    answer_log: list[dict[str, Any]] = field(default_factory=list)
    core_terminal: dict[str, Any] | None = None


@dataclass
class SecondOpinionResult:
    status: str  # "unavailable" | "success" | "error"
    content: str | None = None
    reason: str | None = None
    model: str | None = None


class SecondOpinionProvider(ABC):
    name: str = "unknown"

    @abstractmethod
    async def generate(self, ctx: SecondOpinionContext) -> SecondOpinionResult: ...
