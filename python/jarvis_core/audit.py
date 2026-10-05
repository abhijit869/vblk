"""Structured audit records for JARVIS runtime actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any


@dataclass(frozen=True)
class AuditRecord:
    request_id: str
    event: str
    actor: str
    target: str
    status: str
    timestamp: float = field(default_factory=time)
    metadata: dict[str, Any] = field(default_factory=dict)


class InMemoryAuditLog:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def append(self, record: AuditRecord) -> None:
        self._records.append(record)

    def records(self) -> list[AuditRecord]:
        return list(self._records)
