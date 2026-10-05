# JARVIS OS Architecture

## Vision

JARVIS OS is a Debian-based AI-native operating environment. It should feel like a computer whose operating layer understands goals, state, tools, failures, and recovery rather than a conventional desktop with a chatbot attached.

The system must remain usable when cloud AI is unavailable. Deterministic local software handles normal operating-system tasks whenever AI is unnecessary.

## Base Stack

```text
Debian
Linux kernel
systemd
D-Bus
JARVIS Runtime
JARVIS AI
JARVIS Desktop
```

JARVIS OS does not replace the Linux kernel. It progressively adds a controlled runtime, service layer, AI gateway, security policy, diagnostics, recovery, and custom desktop environment.

## Control Flow

AI never directly controls Linux.

```text
User
JARVIS Core
AI Router
AI Provider
Tool Router
Policy Engine
OS Tool
Linux
Result
Verification
Audit Log
```

Every tool call has a typed schema, risk level, authorization requirement, timeout, audit record, result, and verification status where appropriate.

## AI Architecture

The AI architecture is cloud-first with a restricted local emergency fallback.

```text
Cloud healthy -> Cloud AI
Cloud timeout -> retry
Cloud unavailable -> Local Emergency AI
Cloud recovered -> Cloud AI
```

The local model is limited to basic commands, diagnostics, simple recovery planning, and restricted tool routing. It never receives unrestricted root capability.

## Major Subsystems

### JARVIS Core

Owns request routing, task lifecycle, service health, and subsystem coordination.

### AI Gateway

Provides provider abstraction for authentication, model selection, streaming, tool calling, timeout, retry, rate-limit handling, health checks, fallback, cost tracking, request IDs, and structured responses.

### Tool Router

Routes typed tool calls to deterministic tools. It validates schemas, applies policy, records audit events, enforces timeouts, limits output, and returns structured results.

### Policy Engine

Classifies risk, enforces permissions, blocks unsafe actions, and requires authorization for high-risk operations.

### Terminal Engine

Runs commands through a controlled PTY layer. It captures stdout, stderr, exit code, signal, duration, working directory, truncation status, redaction status, and cancellation status.

### Knowledge Engine

Maintains queryable system knowledge across hardware, software, processes, services, drivers, packages, filesystem, network, users, permissions, configuration, logs, and events.

### System Twin

Tracks system state over time so diagnostics can answer questions such as what changed before a failure or which process consumed memory before pressure began.

### Event Bus

Publishes events such as service failures, process crashes, disk pressure, memory pressure, package updates, driver errors, and configuration changes.

### Memory

Starts with SQLite for preferences, sessions, tasks, incidents, diagnostics, repairs, and system changes. A vector database is deferred until semantic retrieval is required.

### Diagnostics Engine

Turns failures into evidence-backed diagnoses with severity, subsystem, root cause, confidence, possible causes, recommended actions, verification procedure, and rollback procedure.

### Recovery Engine

Uses the sequence detect, diagnose, plan, authorize, snapshot, repair, verify. Failed verification creates new evidence and an alternative repair within strict limits.

### Desktop

Provides AI-first views for Home, Assistant, Terminal, System Monitor, Processes, Services, Files, Network, Security, Recovery, and Settings.

## Service Model

Planned systemd services:

```text
jarvis-core.service
jarvis-ai.service
jarvis-agent.service
jarvis-tools.service
jarvis-memory.service
jarvis-events.service
jarvis-monitor.service
jarvis-diagnostics.service
jarvis-recovery.service
jarvis-security.service
jarvis-ui.service
jarvis-update.service
```

Each service must define dependencies, restart policy, logging, health checks, and graceful shutdown behavior.

## Build Strategy

Development starts outside the ISO. The Debian ISO extraction is a local artifact for inspection. The source of truth should be tracked packages, overlays, service definitions, and build scripts. Custom ISO work begins only after core components are packaged and testable.
