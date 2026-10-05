"""Typed protocol objects for JARVIS tool execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from time import monotonic
from typing import Any
from uuid import uuid4


class RiskLevel(IntEnum):
    READ = 10
    LOW = 20
    MEDIUM = 30
    HIGH = 40
    CRITICAL = 50


def empty_parameters() -> dict[str, Any]:
    return {"type": "object", "properties": {}, "additionalProperties": False}


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    version: int
    risk: RiskLevel
    requires_authorization: bool
    timeout_ms: int
    output_limit_bytes: int
    description: str
    parameters: dict[str, Any] = field(default_factory=empty_parameters)


@dataclass(frozen=True)
class ToolRequest:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    caller: str = "jarvis-core"
    request_id: str = field(default_factory=lambda: f"req_{uuid4().hex}")
    max_risk: RiskLevel = RiskLevel.READ
    authorized: bool = False
    timeout_ms: int | None = None


@dataclass(frozen=True)
class ToolError:
    code: str
    message: str


@dataclass(frozen=True)
class ToolResult:
    request_id: str
    tool: str
    status: str
    risk: RiskLevel
    duration_ms: int
    redacted: bool
    truncated: bool
    data: dict[str, Any] | list[Any] | None
    error: ToolError | None = None


class Timer:
    def __init__(self) -> None:
        self._start = monotonic()

    def elapsed_ms(self) -> int:
        return int((monotonic() - self._start) * 1000)
