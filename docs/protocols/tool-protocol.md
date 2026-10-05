# Tool Protocol

The tool protocol defines how JARVIS components request deterministic operating-system actions.

## Tool Definition

Each tool definition must include:

```yaml
name: system.cpu
version: 1
risk: READ
requires_authorization: false
timeout_ms: 2000
output_limit_bytes: 32768
redaction: standard
verifies_state: false
```

## Tool Request

```json
{
  "request_id": "req_123",
  "caller": "jarvis-agent",
  "tool": "system.cpu",
  "arguments": {},
  "max_risk": "READ",
  "timeout_ms": 2000
}
```

## Tool Result

```json
{
  "request_id": "req_123",
  "tool": "system.cpu",
  "status": "ok",
  "risk": "READ",
  "duration_ms": 12,
  "redacted": false,
  "truncated": false,
  "data": {
    "load_average": [0.1, 0.2, 0.3]
  },
  "error": null
}
```

## AI Gateway Request

```json
{
  "request_id": "ai_123",
  "prompt": "What is my CPU usage?",
  "model": "mock-intent-router",
  "timeout_ms": 5000
}
```

## AI Gateway Response

```json
{
  "request_id": "ai_123",
  "provider": "mock",
  "model": "mock-intent-router",
  "content": "Selected system.cpu",
  "tool_calls": [
    {
      "tool": "system.cpu",
      "arguments": {}
    }
  ]
}
```

The current v0.1 implementation uses a deterministic mock provider. Real cloud providers must be added behind the same gateway interface and must not be called directly from tool or OS code.

## Audit Record

```json
{
  "request_id": "req_123",
  "event": "tool.result",
  "actor": "system.cpu",
  "target": "jarvis-core",
  "status": "ok",
  "timestamp": 1791178300.0,
  "metadata": {}
}
```

Audit records are created for AI requests, AI responses, tool requests, and tool results.

## Error Result

```json
{
  "request_id": "req_123",
  "tool": "service.restart",
  "status": "denied",
  "risk": "MEDIUM",
  "duration_ms": 1,
  "redacted": false,
  "truncated": false,
  "data": null,
  "error": {
    "code": "authorization_required",
    "message": "service.restart requires explicit authorization"
  }
}
```

## Initial Tool Set

Milestone 002 may define schemas for read-only tools only:

```text
system.info
system.cpu
system.memory
system.disk
process.list
service.list
terminal.execute
```

Mutation tools must wait for policy enforcement and audit logging.

## Terminal Result

`terminal.execute` currently accepts only controlled requests and classifies command risk before execution. The default caller risk limit is `READ`.

```json
{
  "command": ["pwd"],
  "risk": "READ",
  "stdout": "/workspaces/vblk\n",
  "stderr": "",
  "exit_code": 0,
  "signal": null,
  "duration_ms": 3,
  "cwd": "/workspaces/vblk",
  "timed_out": false,
  "truncated": false,
  "redacted": false
}
```

High-risk commands are denied before execution when the caller limit is `READ`.
