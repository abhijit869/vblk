import re

with open("python/jarvis_core/config.py", "r") as f:
    content = f.read()

# Add import
if "LocalLlamaProvider" not in content:
    content = content.replace(
        "MockAIProvider, OpenAICompatibleProvider",
        "MockAIProvider, OpenAICompatibleProvider, LocalLlamaProvider"
    )

# Add to CLOUD_PROVIDERS just in case, or handle it in fallback
# We modify build_ai_gateway to use local-llama
fallback_logic = """
    elif config.fallback == "local-llama":
        from jarvis_core.ai_gateway import LocalLlamaProvider
        fallback_provider = LocalLlamaProvider(
            model=os.environ.get("JARVIS_LOCAL_AI_MODEL", "qwen3-1.7b-q4_k_m"),
            base_url=os.environ.get("JARVIS_LOCAL_AI_BASE_URL", "http://127.0.0.1:8081/v1"),
            timeout_ms=int(os.environ.get("JARVIS_LOCAL_TIMEOUT", "120000"))
        )
"""
if "local-llama" not in content:
    content = content.replace(
        'elif config.fallback == "mock":',
        fallback_logic.strip() + '\n    elif config.fallback == "mock":'
    )

with open("python/jarvis_core/config.py", "w") as f:
    f.write(content)
