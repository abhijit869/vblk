# Milestone 002: JARVIS v0.1

## Goal

Build the first working AI control loop:

```text
Natural language
JARVIS Core
Tool selection
Policy check
Read-only Linux tool
Structured result
```

## Current Implementation

Implemented:

```text
python/jarvis_core/ai_gateway.py
python/jarvis_core/audit.py
python/jarvis_core/protocol.py
python/jarvis_core/policy.py
python/jarvis_core/tools.py
python/jarvis_core/core.py
python/jarvis_core/cli.py
tests/unit/
tests/integration/
```

Available tools:

```text
system.info
system.cpu
system.memory
system.disk
process.list
service.list
terminal.execute
```

## Safety Boundary

v0.1 only allows READ-level tools. No package installation, service mutation, file writes, deletion, root commands, GUI actions, or repair actions are included.

## Acceptance Criteria

- Natural-language CPU requests select `system.cpu`.
- Requests pass through the AI Gateway abstraction.
- The default provider is a deterministic offline mock.
- Tool calls return structured results.
- AI requests, AI responses, tool requests, and tool results produce audit records.
- Policy denies tools above the caller risk limit.
- Unknown tools return structured errors.
- Terminal commands are classified by risk before execution.
- Terminal output is captured, redacted, truncated, and timed.
- Process command strings are redacted and capped.
- Tests pass without root privileges.
- Tests run with Python's standard `unittest` runner.

## Next Work

1. Add network read-only tools.
2. Add file metadata/search read-only tools.
3. Add persistent SQLite memory.
4. Add cloud provider configuration interface without committing secrets.
5. Add local fallback provider interface.
