# JARVIS OS

JARVIS OS is an AI-native Linux operating environment built on Debian. The project starts as a controlled runtime, tool, security, memory, diagnostics, and desktop layer on top of Debian instead of replacing the Linux kernel.

The current repository is in the foundation phase. It defines the architecture, security model, protocol boundaries, development workflow, and milestone plan before adding runtime code.

## Architecture

Initial stack:

```text
Debian
Linux kernel
systemd
D-Bus
JARVIS system services
JARVIS Runtime
JARVIS Tool Router
Policy Engine
AI Gateway
JARVIS Desktop
```

Core rule: AI never controls Linux directly. Requests flow through typed tools, policy checks, audit logging, output redaction, timeouts, and verification.

## Repository Layout

```text
crates/          Rust components for policy, runtime, terminal, and security-sensitive code
python/          Python packages for AI orchestration, tools, memory, diagnostics, and agents
desktop/         JARVIS Desktop source
systemd/         Service unit files
docs/            Architecture, protocols, runbooks, and product docs
plans/           Roadmap and milestone plans
tests/           Unit, integration, security, and recovery tests
packaging/       Debian packaging work
iso/             ISO overlays and build configuration
```

## Current Status

- Official Debian 13.7.0 amd64 netinst ISO downloaded locally.
- ISO extracted locally for inspection.
- Repository foundation created.
- JARVIS v0.1 prototype includes an offline AI Gateway mock, read-only natural-language routing, policy-checked tools, audit records, process/service inspection, secret redaction, and controlled terminal execution.

## Run The Prototype

```bash
PYTHONPATH=python python3 -m jarvis_core.cli "What is my CPU usage?"
```

## Test

```bash
PYTHONPATH=python python3 -m unittest discover -s tests
```

Current safe example:

```bash
PYTHONPATH=python python3 -m jarvis_core.cli "Run terminal command"
```

## Next Task

Start JARVIS v0.2 by adding read-only network tools, file metadata/search tools, and SQLite memory for sessions, tool calls, and incidents.
