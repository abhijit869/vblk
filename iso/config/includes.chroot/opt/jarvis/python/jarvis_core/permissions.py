"""Permission Engine for JARVIS OS.

Role-Based Access Control (RBAC) defining what the AI can do on the OS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class Role:
    name: str
    allowed_risk_level: Literal["READ", "MEDIUM", "HIGH"]
    allowed_tools: list[str] | Literal["*"] = "*"
    blocked_tools: list[str] | None = None
    allow_network_sandbox: bool = False
    allow_rw_sandbox: list[str] | None = None


# Default OS Roles
ROLES = {
    "guest": Role(
        name="guest",
        allowed_risk_level="READ",
        allowed_tools=["system.info", "system.cpu", "system.memory"],
        blocked_tools=["terminal.execute", "security.block_ip", "file.write"],
    ),
    "user": Role(
        name="user",
        allowed_risk_level="MEDIUM",
        allowed_tools="*",
        blocked_tools=["security.block_ip"],
        allow_network_sandbox=True,
        allow_rw_sandbox=["/home/user"],
    ),
    "admin": Role(
        name="admin",
        allowed_risk_level="HIGH",
        allowed_tools="*",
        blocked_tools=None,
        allow_network_sandbox=True,
        allow_rw_sandbox=["/"],
    ),
    "jarvis_system": Role(
        name="jarvis_system",
        allowed_risk_level="HIGH",
        allowed_tools="*",
        allow_network_sandbox=True,
        allow_rw_sandbox=["/"],
    )
}


class PermissionEngine:
    def __init__(self, active_role: str = "user"):
        self.role = ROLES.get(active_role, ROLES["guest"])

    def can_execute_tool(self, tool_name: str, risk_level: str) -> bool:
        """Check if the current role is authorized to execute a specific tool."""
        # Check explicit blocks
        if self.role.blocked_tools and tool_name in self.role.blocked_tools:
            return False
            
        # Check explicit allows
        if self.role.allowed_tools != "*" and tool_name not in self.role.allowed_tools:
            return False

        # Map string risk levels to numeric equivalents for comparison
        risk_map = {"READ": 10, "MEDIUM": 20, "HIGH": 30}
        role_risk = risk_map.get(self.role.allowed_risk_level, 10)
        tool_risk = risk_map.get(risk_level, 30) # Default unknown tools to highest risk

        return role_risk >= tool_risk

    def get_sandbox_config(self) -> tuple[bool, list[str]]:
        """Return (allow_network, rw_paths) based on role."""
        return self.role.allow_network_sandbox, (self.role.allow_rw_sandbox or [])
