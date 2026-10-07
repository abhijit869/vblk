# JARVIS OS Architecture

## Vision
JARVIS OS is an **AI-native operating system** built on a **Debian 12 (Bookworm)** foundation. The OS completely redesigns the user experience to be intelligent, proactive, and resilient. It is not merely Debian with an AI assistant attached. 

## 1. System Foundation & Desktop Environment
The underlying foundation is robust Linux, while the user-facing interface is progressively completely redesigned.

- **Debian 12 (Bookworm) / Linux Foundation** [IMPLEMENTED]
- **Desktop Environment (MacTahoe / Openbox)** [PARTIALLY IMPLEMENTED / IN DEVELOPMENT]
- **File Manager** [PLANNED]
- **Applications & Launcher** [PLANNED]
- **Navigation & Settings** [PLANNED]
- **Networking UI & Control** [PLANNED]
- **System Management & Monitoring** [PLANNED]

## 2. JARVIS Platform & AI Layers
The intelligence is provided by the JARVIS Core, driving autonomous action through an Event Bus.

- **AI Gateway** [IMPLEMENTED]
- **Cloud AI Primary** [IMPLEMENTED]
- **Local Qwen3 Fallback (Emergency Reasoning Brain)** [IMPLEMENTED]
- **Tool Registry** [IMPLEMENTED]
- **Policy Engine** [IMPLEMENTED]
- **Diagnostics Engine** [IMPLEMENTED]
- **Recovery Engine** [PLANNED]
- **Memory (SQLite / Vector)** [PARTIALLY IMPLEMENTED]
- **Event Bus** [IMPLEMENTED]
- **Security & Sandboxing (bwrap)** [IMPLEMENTED]

## 3. Architecture Workflow & Control Flow
AI never directly controls Linux.

```text
User / Event Bus
       ↓
   JARVIS Core
       ↓
   AI Gateway
       ↓
 Cloud primary
       ↓ (failure threshold / circuit breaker)
 Local Qwen3 Fallback (CPU-only, llama.cpp b11429)
       ↓ (localhost OpenAI-compatible API)
 JARVIS Tool Provider (Native JSON tool schemas)
       ↓
  Policy Engine
       ↓
  Tool Registry
       ↓
    Linux
```

### Local AI Architecture specifics
The local model (Qwen3-1.7B-Q4_K_M) is **THE EMERGENCY REASONING BRAIN**.
It is NOT the policy authority. It does NOT receive unrestricted root shell access. All actions are subject to strict policy engine and tool registry boundaries.

## 4. Hardware and Runtime Environment
- **CPU ONLY**: No GPU is required (CUDA, Vulkan, ROCm, Metal are explicitly disabled).
- **Virtual Machines**: Target profiles are 2GB (minimum target) and 4GB (preferred).
