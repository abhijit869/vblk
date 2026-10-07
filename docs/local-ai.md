# Local AI (Qwen3-1.7B Fallback)

JARVIS OS integrates an emergency local fallback brain running **Qwen3-1.7B-Q4_K_M** in CPU-only mode via a pinned instance of `llama.cpp` (b11429).

For detailed information on the offline AI capability, please refer to:
- [Local AI Model Details](local-ai-model.md): Specifications on the GGUF model, exact parameters, and llama.cpp runtime constraints.
- [Local AI Fallback Logic](local-ai-fallback.md): Details on the circuit breaker mechanism, lifecycle management, native tool-calling architecture, and recovery.
- [Local AI Testing & Validation](local-ai-testing.md): Information regarding VM profiles (2GB minimum target, 4GB preferred), security constraints, and QEMU compliance matrices (VMware is blocked).
