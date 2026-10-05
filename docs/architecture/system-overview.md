# System Overview

JARVIS OS is built as a set of small, testable services layered on Debian.

## Runtime Boundaries

```text
Clients:
  Desktop
  Terminal UI
  Voice UI
  CLI

Core:
  JARVIS Core
  Agent Planner
  AI Gateway
  Tool Router

Safety:
  Policy Engine
  Permission Engine
  Risk Classifier
  Audit Logger
  Secret Redactor

System:
  Tools
  Terminal Engine
  Knowledge Engine
  Event Bus
  Monitor
  Memory
  Diagnostics
  Recovery
```

## Data Flow

1. A user makes a request.
2. JARVIS Core creates a request ID.
3. The AI Gateway selects a tool call through a provider abstraction.
4. The Tool Router validates requested tools.
5. The Policy Engine authorizes or denies action.
6. The OS Tool executes with a timeout and output limits.
7. Results are redacted, logged, and returned.
8. Verification runs when the action changes state.

The v0.1 prototype uses an offline mock AI provider. This proves the routing and policy shape before adding real cloud credentials or network calls.

## State Flow

The Knowledge Engine and System Twin store summarized system state. The AI queries relevant facts instead of receiving the entire machine state.

## Distribution Flow

The project should generate packages and overlays first. A custom ISO should be assembled from those artifacts later.
