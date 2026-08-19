"""The AI 'second opinion' is pluggable and optional. It is built off the
same generic result payload every protocol produces (headlines, track
evidence, unassessed lists) -- never off protocol-specific field names, so a
new disease protocol doesn't require touching this file."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class SecondOpinionContext:
    core: dict[str, Any]
    protocols: list[dict[str, Any]]  # serialized protocol results (see engine_service.serialize_protocol_result)


@dataclass
class SecondOpinionResult:
    status: str  # "unavailable" | "success" | "error"
    content: str | None = None
    reason: str | None = None


class SecondOpinionProvider(ABC):
    name: str = "unknown"

    @abstractmethod
    async def generate(self, ctx: SecondOpinionContext) -> SecondOpinionResult: ...
