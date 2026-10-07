# JARVIS OS - Local AI Fallback Architecture

The **AI Gateway** in JARVIS OS is designed to be highly resilient. While the primary intelligence is driven by cloud providers (e.g., Google Gemini, OpenAI), the system must never fail catastrophically if network connectivity drops or the cloud API rate limits are exceeded.

## 1. Circuit Breaker Mechanism

The AI Gateway implements a strict **Circuit Breaker** pattern:
*   **Threshold**: 2 consecutive failures from the primary Cloud AI provider.
*   **State Transition**: `HEALTHY` → `DEGRADED` → `UNAVAILABLE`.
*   **Action**: Once marked `UNAVAILABLE`, all subsequent requests are seamlessly routed to the `LocalLlamaProvider`.

## 2. Local AI Lifecycle Management

The local emergency brain (`Qwen3-1.7B-Q4_K_M`) is heavy on memory (approx. 1.2GB resident memory) and is therefore not always kept in active RAM, depending on the `JARVIS_LOCAL_AI_START_MODE`.

1.  **On-Demand Spin-up**: When a fallback occurs, the Gateway attempts to query the local API (`http://127.0.0.1:8081`).
2.  **Sudoers Lifecycle Wrapper**: If the service is down, the Gateway invokes `/usr/lib/jarvis/scripts/local-ai-lifecycle.sh start`. This script is explicitly allowlisted in `/etc/sudoers.d/jarvis-local-ai`.
3.  **Security Constraint**: The wrapper script is locked down and rejects arbitrary arguments (like `bash`, `--exec`), ensuring the AI Gateway cannot be exploited to gain root execution.

## 3. Fallback Tool Calling & Reasoning

When offline:
1.  The `LocalLlamaProvider` receives the standard JARVIS request.
2.  It uses the native OpenAI tool-calling schema seamlessly. The legacy XML `<tools>` parsing workaround was abandoned since `llama.cpp` `b11429` handles JSON structured tool calls natively.
3.  The Qwen3 model processes the request natively on the CPU.
4.  The output is rigorously parsed by the gateway, discarding unknown tool attempts.
5.  The valid tool call is passed to the **Policy Engine** for authorization, exactly as a cloud request would be.

## 4. Recovery & Healing

The Gateway performs bounded background health checks on the primary cloud provider.
*   Once the cloud provider returns `200 OK` consistently, the circuit breaker resets.
*   Traffic is instantly routed back to the primary Cloud AI.
*   The `llama-server` may remain idle or be terminated by an idle timeout to free up memory for standard OS operations.
