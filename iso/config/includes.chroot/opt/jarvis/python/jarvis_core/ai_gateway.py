"""AI Gateway: provider abstraction, retry, fallback, and providers.

The gateway is the only component that talks to AI models. Tools and OS code
never call providers directly. Providers implement two operations:

``complete``  Choose tool calls for a user request.
``respond``   Turn redacted tool results into a natural-language answer.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol
from urllib.parse import urlparse
from uuid import uuid4

from jarvis_core.redaction import redact_text

DEFAULT_SYSTEM_PROMPT = (
    "You are JARVIS, the control layer of a Linux operating system. "
    "You can only observe or change the system by calling the provided tools. "
    "Never invent system facts: call a tool to get them. Prefer dedicated tools over terminal.execute. "
    "terminal.execute accepts one read-only command without shell syntax; mutating commands are denied by policy. "
    "When you receive tool results, answer the user concisely using only those results. "
    "If a tool was denied or failed, say so plainly."
)


class ProviderStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ProviderHealth:
    provider: str
    status: ProviderStatus
    message: str = ""


@dataclass(frozen=True)
class AIToolSpec:
    name: str
    description: str
    parameters: dict[str, Any] = field(
        default_factory=lambda: {"type": "object", "properties": {}, "additionalProperties": False}
    )


@dataclass(frozen=True)
class AIRequest:
    prompt: str
    request_id: str = field(default_factory=lambda: f"ai_{uuid4().hex}")
    model: str | None = None
    timeout_ms: int = 30000
    tools: tuple[AIToolSpec, ...] = ()
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


@dataclass(frozen=True)
class AIToolCall:
    tool: str
    arguments: dict[str, object] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"call_{uuid4().hex[:16]}")


@dataclass(frozen=True)
class AIToolOutput:
    """A tool result handed back to the model. ``content`` must already be redacted."""

    call: AIToolCall
    content: str


@dataclass(frozen=True)
class AIUsage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True)
class AIResponse:
    request_id: str
    provider: str
    model: str
    content: str
    tool_calls: list[AIToolCall] = field(default_factory=list)
    usage: AIUsage | None = None
    fallback_from: str | None = None
    error: str | None = None


class ProviderError(Exception):
    def __init__(self, message: str, retryable: bool = False, retry_after_s: float | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.retry_after_s = retry_after_s


class AIProvider(Protocol):
    name: str

    def health(self) -> ProviderHealth:
        ...

    def complete(self, request: AIRequest) -> AIResponse:
        ...

    def respond(self, request: AIRequest, outputs: Sequence[AIToolOutput]) -> AIResponse:
        ...


# --------------------------------------------------------------------------- #
# Mock provider
# --------------------------------------------------------------------------- #

INTENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("system.cpu", re.compile(r"\b(cpu|processor|load|slow)\b")),
    ("system.memory", re.compile(r"\b(memory|ram|swap)\b")),
    ("system.disk", re.compile(r"\b(disk|storage|space|drive)\b")),
    ("process.list", re.compile(r"\b(process(es)?|running (apps?|programs?))\b")),
    ("service.list", re.compile(r"\b(services?|daemons?|systemd)\b")),
]
TERMINAL_PATTERN = re.compile(r"\b(terminal|shell|command)\b")


class MockAIProvider:
    """Deterministic offline provider used for tests, development, and fallback."""

    name = "mock"

    def __init__(self, model: str = "mock-intent-router", status: ProviderStatus = ProviderStatus.HEALTHY) -> None:
        self._model = model
        self._status = status

    def health(self) -> ProviderHealth:
        return ProviderHealth(provider=self.name, status=self._status)

    def complete(self, request: AIRequest) -> AIResponse:
        if self._status == ProviderStatus.UNAVAILABLE:
            return AIResponse(
                request_id=request.request_id,
                provider=self.name,
                model=self._model,
                content="Provider unavailable",
                tool_calls=[],
            )

        tool_calls = self._select_tool_calls(request.prompt)
        return AIResponse(
            request_id=request.request_id,
            provider=self.name,
            model=self._model,
            content="Selected " + ", ".join(call.tool for call in tool_calls),
            tool_calls=tool_calls,
        )

    def respond(self, request: AIRequest, outputs: Sequence[AIToolOutput]) -> AIResponse:
        lines = [_summarize_output(output) for output in outputs]
        return AIResponse(
            request_id=request.request_id,
            provider=self.name,
            model=self._model,
            content="\n".join(lines) if lines else "No tools were run.",
        )

    def _select_tool_calls(self, prompt: str) -> list[AIToolCall]:
        normalized = prompt.lower()
        calls = [AIToolCall(tool) for tool, pattern in INTENT_PATTERNS if pattern.search(normalized)]
        if calls:
            return calls
        if TERMINAL_PATTERN.search(normalized):
            return [AIToolCall("terminal.execute", {"command": "pwd"})]
        return [AIToolCall("system.info")]


def _summarize_output(output: AIToolOutput) -> str:
    tool = output.call.tool
    try:
        result = json.loads(output.content)
    except json.JSONDecodeError:
        return f"{tool}: {output.content[:200]}"

    status = result.get("status")
    data = result.get("data")
    error = result.get("error") or {}
    if status == "denied" and tool == "terminal.execute" and isinstance(data, dict):
        return f"I did not run `{' '.join(data.get('command', []))}`: {error.get('message', 'denied by policy')}."
    if status != "ok":
        return f"{tool} {status}: {error.get('message', 'no details')}."

    summarizer = _SUMMARIZERS.get(tool)
    if summarizer is None or data is None:
        return f"{tool}: {json.dumps(data)[:300]}"
    try:
        return summarizer(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return f"{tool}: {json.dumps(data)[:300]}"


def _gib(kb_or_bytes: float, unit: str = "kb") -> str:
    divisor = 1024**2 if unit == "kb" else 1024**3
    return f"{kb_or_bytes / divisor:.1f} GiB"


def _summarize_cpu(data: dict[str, Any]) -> str:
    count = data["cpu_count"]
    load = data.get("load_average")
    if not load:
        return f"You have {count} CPU cores. Load average is not available."
    busy = min(100.0, load[0] / count * 100)
    return (
        f"You have {count} CPU cores. Load average (1/5/15 min): "
        f"{load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f} (about {busy:.0f}% of capacity over the last minute)."
    )


def _summarize_memory(data: dict[str, Any]) -> str:
    total, used, available = data["total_kb"], data["used_kb"], data["available_kb"]
    return (
        f"Memory: {_gib(used)} used of {_gib(total)} ({used / total * 100:.0f}%), "
        f"{_gib(available)} available."
    )


def _summarize_disk(data: dict[str, Any]) -> str:
    total, used, free = data["total_bytes"], data["used_bytes"], data["free_bytes"]
    return (
        f"Disk {data['path']}: {_gib(used, 'b')} used of {_gib(total, 'b')} "
        f"({used / total * 100:.0f}%), {_gib(free, 'b')} free."
    )


def _summarize_processes(data: list[dict[str, Any]]) -> str:
    top = sorted(data, key=lambda process: process.get("vm_rss_kb") or 0, reverse=True)[:5]
    listed = ", ".join(f"{p['name']} (pid {p['pid']}, {(p.get('vm_rss_kb') or 0) / 1024:.0f} MiB)" for p in top)
    return f"{len(data)} processes running. Largest by memory: {listed}."


def _summarize_services(data: list[dict[str, Any]]) -> str:
    active = sum(1 for service in data if service.get("active") == "active")
    failed = [service["unit"] for service in data if service.get("active") == "failed"]
    text = f"{len(data)} services: {active} active, {len(failed)} failed"
    return text + (f" ({', '.join(failed[:10])})." if failed else ".")


def _summarize_terminal(data: dict[str, Any]) -> str:
    command = " ".join(data.get("command", []))
    if data.get("timed_out"):
        return f"`{command}` timed out."
    output = (data.get("stdout") or data.get("stderr") or "").strip()
    return f"Ran `{command}` (exit {data.get('exit_code')}):\n{output}"


def _summarize_info(data: dict[str, Any]) -> str:
    return f"{data['system']} {data['release']} on {data['machine']} (Python {data['python_version']})."


_SUMMARIZERS: dict[str, Callable[[Any], str]] = {
    "system.cpu": _summarize_cpu,
    "system.memory": _summarize_memory,
    "system.disk": _summarize_disk,
    "process.list": _summarize_processes,
    "service.list": _summarize_services,
    "terminal.execute": _summarize_terminal,
    "system.info": _summarize_info,
}


# --------------------------------------------------------------------------- #
# OpenAI-compatible provider (OpenAI, and servers exposing the same API such as
# vLLM, llama.cpp server, or Ollama's /v1 endpoint)
# --------------------------------------------------------------------------- #

_FUNCTION_NAME_INVALID = re.compile(r"[^a-zA-Z0-9_-]")


def encode_tool_name(name: str) -> str:
    """Map a JARVIS tool name to the provider pattern ``^[a-zA-Z0-9_-]{1,64}$``."""
    return _FUNCTION_NAME_INVALID.sub("_", name)[:64]


class OpenAICompatibleProvider:
    """Chat Completions provider with function calling, using only the stdlib."""

    name = "openai-compatible"

    def __init__(
        self,
        model: str | None,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_ms: int = 30000,
        name: str | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_ms = timeout_ms
        if name:
            self.name = name

    def __repr__(self) -> str:  # never expose the API key
        return f"OpenAICompatibleProvider(name={self.name!r}, model={self._model!r}, base_url={self._base_url!r})"

    def health(self) -> ProviderHealth:
        if not self._model:
            return ProviderHealth(self.name, ProviderStatus.UNAVAILABLE, "JARVIS_AI_MODEL is not set")
        if not self._api_key and not _is_local_url(self._base_url):
            return ProviderHealth(self.name, ProviderStatus.UNAVAILABLE, "JARVIS_AI_API_KEY is not set")
        return ProviderHealth(self.name, ProviderStatus.HEALTHY)

    def complete(self, request: AIRequest) -> AIResponse:
        name_map = {encode_tool_name(spec.name): spec.name for spec in request.tools}
        body: dict[str, Any] = {
            "model": request.model or self._model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.prompt},
            ],
        }
        if request.tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": encode_tool_name(spec.name),
                        "description": spec.description,
                        "parameters": spec.parameters,
                    },
                }
                for spec in request.tools
            ]
            body["tool_choice"] = "auto"

        payload = self._post("/chat/completions", body, request.timeout_ms)
        message = _first_message(payload)
        tool_calls = [
            _parse_tool_call(raw, name_map) for raw in message.get("tool_calls") or [] if raw.get("type") == "function"
        ]
        return AIResponse(
            request_id=request.request_id,
            provider=self.name,
            model=str(payload.get("model") or body["model"]),
            content=message.get("content") or "",
            tool_calls=tool_calls,
            usage=_parse_usage(payload),
        )

    def respond(self, request: AIRequest, outputs: Sequence[AIToolOutput]) -> AIResponse:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.prompt},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": output.call.id,
                        "type": "function",
                        "function": {
                            "name": encode_tool_name(output.call.tool),
                            "arguments": json.dumps(output.call.arguments),
                        },
                    }
                    for output in outputs
                ],
            },
        ]
        messages.extend(
            {"role": "tool", "tool_call_id": output.call.id, "content": output.content} for output in outputs
        )
        body = {"model": request.model or self._model, "messages": messages}
        payload = self._post("/chat/completions", body, request.timeout_ms)
        message = _first_message(payload)
        return AIResponse(
            request_id=request.request_id,
            provider=self.name,
            model=str(payload.get("model") or body["model"]),
            content=message.get("content") or "",
            usage=_parse_usage(payload),
        )

    def _post(self, path: str, body: dict[str, Any], timeout_ms: int) -> dict[str, Any]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        http_request = urllib.request.Request(
            self._base_url + path,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        timeout_s = min(timeout_ms, self._timeout_ms) / 1000
        try:
            with urllib.request.urlopen(http_request, timeout=timeout_s) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail, _ = redact_text(exc.read().decode("utf-8", errors="replace")[:300])
            retryable = exc.code == 429 or exc.code >= 500
            retry_after = _parse_retry_after(exc.headers.get("Retry-After") if exc.headers else None)
            raise ProviderError(f"HTTP {exc.code}: {detail}", retryable=retryable, retry_after_s=retry_after) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            reason = getattr(exc, "reason", exc)
            raise ProviderError(f"Connection failed: {reason}", retryable=True) from None

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            raise ProviderError("Provider returned invalid JSON", retryable=True) from None
        if not isinstance(payload, dict):
            raise ProviderError("Provider returned an unexpected payload")
        return payload


def _is_local_url(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local")


def _first_message(payload: dict[str, Any]) -> dict[str, Any]:
    choices = payload.get("choices")
    if not choices or not isinstance(choices, list):
        raise ProviderError("Provider response has no choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ProviderError("Provider response has no message")
    return message


def _parse_tool_call(raw: dict[str, Any], name_map: dict[str, str]) -> AIToolCall:
    function = raw.get("function") or {}
    encoded = str(function.get("name", ""))
    raw_arguments = function.get("arguments") or "{}"
    try:
        arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else dict(raw_arguments)
    except (json.JSONDecodeError, TypeError, ValueError):
        arguments = {"_invalid_arguments": str(raw_arguments)[:200]}
    if not isinstance(arguments, dict):
        arguments = {"_invalid_arguments": str(raw_arguments)[:200]}
    return AIToolCall(
        tool=name_map.get(encoded, encoded),
        arguments=arguments,
        id=str(raw.get("id") or f"call_{uuid4().hex[:16]}"),
    )


def _parse_usage(payload: dict[str, Any]) -> AIUsage | None:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    return AIUsage(
        input_tokens=int(usage.get("prompt_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or 0),
    )


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# Gateway
# --------------------------------------------------------------------------- #


class AIGateway:
    """Routes requests to the primary provider with retry, then to a fallback."""

    def __init__(
        self,
        primary: AIProvider | None = None,
        fallback: AIProvider | None = None,
        max_retries: int = 2,
        backoff_s: float = 0.5,
        max_backoff_s: float = 8.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._primary = primary or MockAIProvider()
        self._fallback = fallback
        self._max_retries = max(0, max_retries)
        self._backoff_s = backoff_s
        self._max_backoff_s = max_backoff_s
        self._sleep = sleep

    @property
    def primary(self) -> AIProvider:
        return self._primary

    @property
    def fallback(self) -> AIProvider | None:
        return self._fallback

    def health(self) -> ProviderHealth:
        return self._primary.health()

    def complete(self, request: AIRequest) -> AIResponse:
        return self._route(request, lambda provider: provider.complete(request))

    def respond(self, request: AIRequest, outputs: Sequence[AIToolOutput]) -> AIResponse:
        return self._route(request, lambda provider: provider.respond(request, outputs))

    def _route(self, request: AIRequest, call: Callable[[AIProvider], AIResponse]) -> AIResponse:
        health = self._primary.health()
        if health.status == ProviderStatus.UNAVAILABLE:
            reason = health.message or "AI provider unavailable"
            return self._use_fallback(request, call, reason)

        try:
            return self._with_retry(self._primary, call)
        except ProviderError as exc:
            return self._use_fallback(request, call, str(exc))

    def _with_retry(self, provider: AIProvider, call: Callable[[AIProvider], AIResponse]) -> AIResponse:
        attempt = 0
        while True:
            try:
                return call(provider)
            except ProviderError as exc:
                if not exc.retryable or attempt >= self._max_retries:
                    raise
                delay = exc.retry_after_s if exc.retry_after_s is not None else self._backoff_s * (2**attempt)
                self._sleep(min(delay, self._max_backoff_s))
                attempt += 1

    def _use_fallback(
        self, request: AIRequest, call: Callable[[AIProvider], AIResponse], reason: str
    ) -> AIResponse:
        if self._fallback is None:
            return AIResponse(
                request_id=request.request_id,
                provider=self._primary.name,
                model=request.model or "unknown",
                content=f"AI provider unavailable: {reason}",
                tool_calls=[],
                error=reason,
            )
        try:
            response = call(self._fallback)
        except ProviderError as exc:
            return AIResponse(
                request_id=request.request_id,
                provider=self._fallback.name,
                model=request.model or "unknown",
                content=f"AI provider unavailable: {reason}; fallback failed: {exc}",
                tool_calls=[],
                error=f"{reason}; fallback failed: {exc}",
            )
        return AIResponse(
            request_id=response.request_id,
            provider=response.provider,
            model=response.model,
            content=response.content,
            tool_calls=response.tool_calls,
            usage=response.usage,
            fallback_from=self._primary.name,
            error=reason,
        )
