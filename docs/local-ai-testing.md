# JARVIS OS - Local AI Testing & Validation

The Local AI Fallback subsystem is rigorously validated against specific low-spec virtual machine profiles to ensure operational stability.

## 1. Validation Criteria

To be marked as `PASS`, the Local AI component (`Qwen3-1.7B-Q4_K_M`) must successfully complete the following chain within a booted JARVIS OS environment (QEMU):

1. **Boot**: The JARVIS OS boots successfully.
2. **Desktop & Core**: The UI and JARVIS Core initialize.
3. **Cloud Failure Detection**: The system correctly detects cloud API unreachability.
4. **Local AI Bootstrapping**: `jarvis-local-ai.service` starts `llama-server`.
5. **Real Inference**: A user prompt is correctly processed by `Qwen3-1.7B`.
6. **Real Tool Call**: The model emits a structured tool call.
7. **Policy Engine**: The tool call passes validation and authorization.
8. **Linux Execution**: The deterministic tool (e.g., `system.cpu`) executes securely.
9. **Final Response**: The LLM consumes the tool output and answers the user.

## 2. Memory Profiles Tested

We explicitly validate JARVIS OS against the following QEMU profiles (No GPU, x86_64).

> [!WARNING]
> VMware testing is explicitly documented as **BLOCKED** due to automation unavailability. Manual validation was performed on QEMU instead.

### 2 GB VM Test (Minimal Resource Target)
*   **vCPUs**: 2
*   **RAM**: 2 GB
*   **Context Limit**: 2048-token context
*   **Expected Behavior**: System operates normally. `zramswap` manages memory pressure during model loading. Inference is slow but steady. No `OOM` kills occur.
*   **Status**: NOT YET PROVEN. 
*   **Evidence**: Model/Process memory measurement showed Idle Resident Memory ~2.2 GB and Inference Peak ~1.87 GB. However, COMPLETE 2 GB JARVIS OS VM ACCEPTANCE requires a full guest boot and inference test, which is not yet proven.

### 4 GB VM Test (Recommended Comfortable Target)
*   **vCPUs**: 4
*   **RAM**: 4 GB
*   **Context Limit**: 4096-token context
*   **Expected Behavior**: Comfortable overhead. The model loads quickly into memory, and standard OS applications remain responsive.
*   **Status**: NOT PROVEN. (Requires complete guest test).
*   **Evidence**: 4096-token context benchmark memory test itself is a PASS, but full guest system test is NOT PROVEN.

## 3. Offline Mode Test
*   **Status**: BLOCKED. 
*   **Evidence**: Only label OFFLINE MODE as PASS after an actual no-network test.

## 4. Tool Call Injection Resistance

Security regression tests (`test_tool_injection.py`) enforce that:
*   Users cannot inject malformed JSON or unknown tools within the native OpenAI tool schemas.
*   The gateway strips unknown tool executions.
*   Malformed JSON or invalid arguments are discarded cleanly without execution.

## 5. Qwen3 Reasoning (Thinking Mode)

Tested against the pinned `llama.cpp` runtime:
*   Qwen3-1.7B organically generates step-by-step reasoning inline when instructed.
*   We validate that the model provides transparent diagnostic thought processes natively without requiring proprietary out-of-band XML channels or hidden API fields.
