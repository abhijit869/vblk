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


import json
import os
from dataclasses import asdict

class InMemoryAuditLog:
    """Persistent audit log, aliased for backward compatibility."""
    def __init__(self, log_path: str = "/var/log/jarvis/audit.jsonl") -> None:
        self._records: list[AuditRecord] = []
        self._log_path = log_path
        
        # Ensure directory exists if we have permissions
        log_dir = os.path.dirname(self._log_path)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except OSError:
                pass

    def append(self, record: AuditRecord) -> None:
        self._records.append(record)
        try:
            with open(self._log_path, "a") as f:
                f.write(json.dumps(asdict(record)) + "\n")
        except OSError:
            # Fallback for tests or missing permissions
            pass

    def records(self) -> list[AuditRecord]:
        return list(self._records)
