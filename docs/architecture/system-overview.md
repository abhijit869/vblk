# System Overview

JARVIS OS is an AI-native operating system built on a **Debian 12 (Bookworm)** foundation.

## Runtime Boundaries

```text
Clients:
  Desktop (MacTahoe/Openbox)
  Terminal UI
  Voice UI
  CLI

Core:
  JARVIS Core
  Agent Planner
  AI Gateway (Cloud Primary / Local Qwen3 Fallback)
  Tool Router

Safety:
  Policy Engine
  Permission Engine
  Risk Classifier
  Audit Logger
  Secret Redactor

System:
  Tools
  Terminal Engine (bwrap sandboxing)
  Knowledge Engine
  Event Bus
  Monitor
  Memory (SQLite)
  Diagnostics
  Recovery
```

## Data Flow

1. A user makes a request or the Event Bus generates a system anomaly.
2. JARVIS Core creates a request ID.
3. The AI Gateway selects a tool call through a provider abstraction (using Cloud AI if healthy, or Local Qwen3 if degraded/offline).
4. The Tool Router validates requested tools using native OpenAI JSON schemas.
5. The Policy Engine authorizes or denies action. (The AI is the reasoning brain, NOT the policy authority).
6. The OS Tool executes securely (via Bubblewrap) with a timeout and output limits.
7. Results are redacted, logged, and returned.
8. Verification runs when the action changes state.

## State Flow

The Knowledge Engine and System Twin store summarized system state. The AI queries relevant facts instead of receiving the entire machine state.

## Distribution Flow

The authoritative build pipeline is `scripts/build/build-iso.sh` which dynamically downloads the Debian base, injects JARVIS, compiles the local inference engine (llama.cpp pinned b11429), and packages everything into an installable ISO.
