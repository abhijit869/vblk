"""Policy enforcement for JARVIS tool execution."""

from __future__ import annotations

from dataclasses import dataclass

from jarvis_core.protocol import ToolDefinition, ToolError, ToolRequest


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    error: ToolError | None = None


class PolicyEngine:
    """Minimal policy engine for v0.1.

    v0.1 only allows read-only tools by default. Higher-risk tools are denied
    until explicit authorization and rollback foundations exist.
    """

    def authorize(
        self, request: ToolRequest, definition: ToolDefinition
    ) -> PolicyDecision:
        if definition.risk > request.max_risk:
            return PolicyDecision(
                allowed=False,
                error=ToolError(
                    code="risk_exceeds_request_limit",
                    message=f"{definition.name} risk {definition.risk.name} exceeds max {request.max_risk.name}",
                ),
            )

        if definition.requires_authorization and not request.authorized:
            return PolicyDecision(
                allowed=False,
                error=ToolError(
                    code="authorization_required",
                    message=f"{definition.name} requires explicit authorization",
                ),
            )

        return PolicyDecision(allowed=True)
