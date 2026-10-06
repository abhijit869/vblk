"""JARVIS v0.1 control loop.

User text
  -> AI Gateway (choose tool calls)
  -> Tool Registry (validate, policy, execute, redact, limit)
  -> AI Gateway (turn redacted results into an answer)
  -> User
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from jarvis_core.ai_gateway import (
    AIGateway,
    AIRequest,
    AIResponse,
    AIToolCall,
    AIToolOutput,
    AIToolSpec,
)
from jarvis_core.audit import AuditRecord, InMemoryAuditLog
from jarvis_core.memory import SQLiteMemoryEngine
from jarvis_core.protocol import RiskLevel, ToolDefinition, ToolRequest, ToolResult
from jarvis_core.redaction import redact_text
from jarvis_core.tools import ToolRegistry, build_default_registry, limit_data

MAX_TOOL_CALLS_PER_REQUEST = 4
AI_RESULT_LIMIT_BYTES = 12000


class JarvisCore:
    def __init__(
        self,
        tools: ToolRegistry | None = None,
        ai_gateway: AIGateway | None = None,
        audit_log: InMemoryAuditLog | None = None,
        memory_engine: SQLiteMemoryEngine | None = None,
        max_risk: RiskLevel = RiskLevel.READ,
    ) -> None:
        self._tools = tools or build_default_registry()
        self._ai_gateway = ai_gateway or AIGateway()
        self._audit_log = audit_log or InMemoryAuditLog()
        self._memory_engine = memory_engine
        self._max_risk = max_risk

    @property
    def audit_log(self) -> InMemoryAuditLog:
        return self._audit_log

    def handle_text(self, text: str, session_id: str | None = None) -> dict[str, Any]:
        if self._memory_engine and not session_id:
            session_id = self._memory_engine.create_session()
        ai_request = AIRequest(
            prompt=text,
            tools=tuple(
                _tool_spec(definition)
                for definition in self._tools.definitions(self._max_risk)
            ),
        )
        self._audit_log.append(
            AuditRecord(
                ai_request.request_id,
                "ai.request",
                "jarvis-core",
                "ai-gateway",
                "started",
            )
        )
        ai_response = self._ai_gateway.complete(ai_request)
        self._audit_ai(ai_request, "ai.response", ai_response)

        if not ai_response.tool_calls:
            if self._memory_engine and session_id:
                self._memory_engine.record_interaction(
                    session_id, text, ai_response.content
                )
            return self._response(
                text, ai_response.content, ai_response, None, [], session_id
            )

        calls = ai_response.tool_calls[:MAX_TOOL_CALLS_PER_REQUEST]
        executed: list[tuple[AIToolCall, ToolResult]] = [
            (call, self._run_tool(call, session_id)) for call in calls
        ]

        outputs = [
            AIToolOutput(call=call, content=_result_for_ai(result))
            for call, result in executed
        ]
        answer = self._ai_gateway.respond(ai_request, outputs)
        self._audit_ai(ai_request, "ai.answer", answer)

        if self._memory_engine and session_id:
            self._memory_engine.record_interaction(session_id, text, answer.content)
        return self._response(
            text, answer.content, ai_response, answer, executed, session_id
        )

    def _run_tool(self, call: AIToolCall, session_id: str | None = None) -> ToolResult:
        request = ToolRequest(
            tool=call.tool,
            arguments=dict(call.arguments),
            caller="jarvis-core",
            max_risk=self._max_risk,
        )
        self._audit_log.append(
            AuditRecord(
                request.request_id,
                "tool.request",
                request.caller,
                request.tool,
                "started",
                metadata={
                    "ai_call_id": call.id,
                    "arguments": _redacted_arguments(request.arguments),
                },
            )
        )
        result = self._tools.execute(request)
        self._audit_log.append(
            AuditRecord(
                request.request_id,
                "tool.result",
                request.tool,
                request.caller,
                result.status,
                metadata={
                    "duration_ms": result.duration_ms,
                    "redacted": result.redacted,
                    "truncated": result.truncated,
                    "error": result.error.code if result.error else None,
                },
            )
        )
        if self._memory_engine and session_id:
            self._memory_engine.record_tool_call(session_id, request, result)
        return result

    def _audit_ai(self, request: AIRequest, event: str, response: AIResponse) -> None:
        metadata: dict[str, Any] = {
            "provider": response.provider,
            "model": response.model,
            "tool_calls": len(response.tool_calls),
        }
        if response.usage:
            metadata["input_tokens"] = response.usage.input_tokens
            metadata["output_tokens"] = response.usage.output_tokens
        if response.fallback_from:
            metadata["fallback_from"] = response.fallback_from
        if response.error:
            metadata["error"] = response.error
        status = "error" if response.error and not response.fallback_from else "ok"
        if event == "ai.response" and not response.tool_calls and status == "ok":
            status = "no_tool"
        self._audit_log.append(
            AuditRecord(
                request.request_id,
                event,
                response.provider,
                "jarvis-core",
                status,
                metadata=metadata,
            )
        )

    def _response(
        self,
        text: str,
        answer: str,
        ai_response: AIResponse,
        answer_response: AIResponse | None,
        executed: list[tuple[AIToolCall, ToolResult]],
        session_id: str | None = None,
    ) -> dict[str, Any]:
        results = [asdict(result) for _, result in executed]
        return {
            "session_id": session_id,
            "input": text,
            "answer": answer,
            "ai": asdict(ai_response),
            "answer_ai": asdict(answer_response) if answer_response else None,
            "selected_tool": executed[0][0].tool if executed else None,
            "selected_tools": [call.tool for call, _ in executed],
            "result": results[0] if results else None,
            "results": results,
            "audit_records": [asdict(record) for record in self._audit_log.records()],
        }


def _tool_spec(definition: ToolDefinition) -> AIToolSpec:
    return AIToolSpec(
        name=definition.name,
        description=definition.description,
        parameters=definition.parameters,
    )


def _result_for_ai(result: ToolResult) -> str:
    """Serialize a tool result for a model: redacted, size-limited JSON."""
    data, truncated = limit_data(result.data, AI_RESULT_LIMIT_BYTES)
    payload = {
        "tool": result.tool,
        "status": result.status,
        "risk": result.risk.name,
        "truncated": result.truncated or truncated,
        "data": data,
        "error": asdict(result.error) if result.error else None,
    }
    text, _ = redact_text(json.dumps(payload, default=str, ensure_ascii=False))
    return text


def _redacted_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    text, _ = redact_text(json.dumps(arguments, default=str))
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_redacted": text}
