# JARVIS OS - Local Emergency AI Brain

JARVIS OS integrates a fully autonomous, offline-capable emergency reasoning brain as a fallback for the primary cloud AI. This ensures the operating system can still diagnose issues, execute tools, and assist the user even in a completely air-gapped or network-failed environment.

## 1. Core Model Specifications

*   **Model Architecture**: Qwen3
*   **Parameter Count**: 1.77 Billion
*   **Quantization**: `Q4_K_M` (GGUF)
*   **Repository**: `ggml-org/Qwen3-1.7B-GGUF`
*   **Filename**: `Qwen3-1.7B-Q4_K_M.gguf`
*   **File Size**: ~1.11 GB (1,282,439,264 bytes)
*   **SHA256 Checksum**: `d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5`
*   **License**: Apache-2.0

## 2. Runtime Engine (`llama.cpp`)

To maximize compatibility with low-spec hardware (e.g., 2GB-4GB Virtual Machines) without requiring specialized hardware, JARVIS OS uses a strictly CPU-only configuration of `llama.cpp`.

*   **Engine**: `llama-server`
*   **Pinned Revision**: Tag `b11429` (Commit `d812350`)
*   **Compilation Flags**: `-DGGML_NATIVE=OFF -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DGGML_METAL=OFF`
*   **Context Size**: 2048 (Expandable up to 4096 depending on VM memory constraints)
*   **Threads**: 2
*   **GPU Layers**: 0 (Strictly enforced)

*Note: Older versions of llama.cpp (e.g., b3901) do not natively support the `qwen3` architecture and will fail to load this model.*

## 3. Tool Calling Workflow

Qwen3-1.7B is configured to support structured tool calls. Because of the upgraded runtime (`b11429`), JARVIS utilizes native OpenAI JSON formatting for tool calls. The legacy XML `<tools>` parsing workaround was abandoned, increasing security and stability against prompt injections.

When the cloud primary fails, the Gateway degrades gracefully, routing requests directly to the `LocalLlamaProvider`, prompting the model to reason step-by-step before generating an actionable JARVIS Tool JSON block.

## 4. Security & System Integration

The Local AI is sandboxed via a dedicated systemd service (`jarvis-local-ai.service`):
*   `User=jarvis`
*   `NoNewPrivileges=true`
*   `ProtectSystem=strict`
*   The model file (`/usr/lib/jarvis/models/emergency/Qwen3-1.7B-Q4_K_M.gguf`) is strictly read-only.
