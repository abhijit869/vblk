"""Permission Engine for JARVIS OS.

Role-Based Access Control (RBAC) defining what the AI can do on the OS.
The active role is enforced by :class:`jarvis_core.tools.ToolRegistry` on every
tool call, and also decides the sandbox network / writable-path settings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from jarvis_core.protocol import RiskLevel

RiskName = Literal["READ", "LOW", "MEDIUM", "HIGH"]

RISK_BY_NAME: dict[str, RiskLevel] = {
    "READ": RiskLevel.READ,
    "LOW": RiskLevel.LOW,
    "MEDIUM": RiskLevel.MEDIUM,
    "HIGH": RiskLevel.HIGH,
    # CRITICAL is deliberately mapped above every role: it is never allowed.
    "CRITICAL": RiskLevel.CRITICAL,
}


@dataclass(frozen=True)
class Role:
    name: str
    allowed_risk_level: RiskName
    allowed_tools: tuple[str, ...] | Literal["*"] = "*"
    blocked_tools: tuple[str, ...] = ()
    allow_network_sandbox: bool = False
    allow_rw_sandbox: tuple[str, ...] = ()

    @property
    def max_risk(self) -> RiskLevel:
        return RISK_BY_NAME[self.allowed_risk_level]


# Default OS Roles
ROLES: dict[str, Role] = {
    "guest": Role(
        name="guest",
        allowed_risk_level="READ",
        allowed_tools=("system.info", "system.cpu", "system.memory"),
        blocked_tools=("terminal.execute", "security.block_ip", "file.write", "file.read", "gui.screenshot"),
    ),
    "user": Role(
        name="user",
        allowed_risk_level="MEDIUM",
        allowed_tools="*",
        blocked_tools=("security.block_ip",),
        allow_network_sandbox=True,
        allow_rw_sandbox=("/home/user",),
    ),
    "admin": Role(
        name="admin",
        allowed_risk_level="HIGH",
        allowed_tools="*",
        allow_network_sandbox=True,
        # Never "/": system paths stay read-only even for admins (see sandbox.FORBIDDEN_RW_PATHS).
        allow_rw_sandbox=("/home", "/srv"),
    ),
    # Role used by the background daemon when no interactive user is present.
    "jarvis_system": Role(
        name="jarvis_system",
        allowed_risk_level="READ",
        allowed_tools="*",
        blocked_tools=("gui.click", "gui.type", "gui.screenshot", "security.block_ip"),
        allow_network_sandbox=False,
    ),
}

DEFAULT_ROLE = "user"


class PermissionEngine:
    def __init__(self, active_role: str | None = None):
        name = active_role or os.environ.get("JARVIS_ROLE") or DEFAULT_ROLE
        # Unknown role names fall back to the least-privileged role.
        self.role = ROLES.get(name, ROLES["guest"])

    @property
    def max_risk(self) -> RiskLevel:
        return self.role.max_risk

    def can_execute_tool(self, tool_name: str, risk_level: str | RiskLevel) -> bool:
        """Check if the current role is authorized to execute a specific tool."""
        # Check explicit blocks
        if tool_name in self.role.blocked_tools:
            return False

        # Check explicit allows
        if self.role.allowed_tools != "*" and tool_name not in self.role.allowed_tools:
            return False

        if isinstance(risk_level, RiskLevel):
            tool_risk = risk_level
        else:
            # Default unknown risk names to CRITICAL (never allowed)
            tool_risk = RISK_BY_NAME.get(str(risk_level).upper(), RiskLevel.CRITICAL)

        if tool_risk >= RiskLevel.CRITICAL:
            return False
        return self.role.max_risk >= tool_risk

    def get_sandbox_config(self) -> tuple[bool, list[str]]:
        """Return (allow_network, rw_paths) based on role."""
        return self.role.allow_network_sandbox, list(self.role.allow_rw_sandbox)
