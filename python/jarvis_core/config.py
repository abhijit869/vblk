"""Runtime configuration loaded from environment variables.

Secrets are read from the environment only and are never written to disk,
logged, or included in reprs.

Environment variables:

``JARVIS_AI_PROVIDER``    ``mock`` | ``openai`` | ``openai-compatible``.
                          Defaults to ``openai`` when an API key is present,
                          otherwise ``mock``.
``JARVIS_AI_API_KEY``     Provider API key (``OPENAI_API_KEY`` is also accepted).
``JARVIS_AI_MODEL``       Model name, required for cloud providers.
``JARVIS_AI_BASE_URL``    API base URL. Default ``https://api.openai.com/v1``.
``JARVIS_AI_TIMEOUT_MS``  Per-request timeout. Default ``30000``.
``JARVIS_AI_MAX_RETRIES`` Retries for transient errors. Default ``2``.
``JARVIS_AI_FALLBACK``    ``mock`` (default) or ``none``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from jarvis_core.ai_gateway import AIGateway, MockAIProvider, OpenAICompatibleProvider, LocalLlamaProvider

DEFAULT_BASE_URL = "https://api.openai.com/v1"
CLOUD_PROVIDERS = {
    "openai",
    "openai-compatible",
    "gemini",
    "antigravity_cli",
    "antigravity",
}


@dataclass(frozen=True)
class AIConfig:
    provider: str = "mock"
    model: str | None = None
    base_url: str = DEFAULT_BASE_URL
    api_key: str | None = field(default=None, repr=False)
    timeout_ms: int = 30000
    max_retries: int = 2
    fallback: str = "mock"


def load_ai_config(env: Mapping[str, str] | None = None) -> AIConfig:
    env = os.environ if env is None else env
    api_key = env.get("JARVIS_AI_API_KEY") or env.get("OPENAI_API_KEY") or None
    provider = (
        (env.get("JARVIS_AI_PROVIDER") or ("openai" if api_key else "mock"))
        .strip()
        .lower()
    )
    if provider not in CLOUD_PROVIDERS | {"mock"}:
        raise ValueError(f"Unsupported JARVIS_AI_PROVIDER: {provider}")
    return AIConfig(
        provider=provider,
        model=env.get("JARVIS_AI_MODEL") or None,
        base_url=env.get("JARVIS_AI_BASE_URL") or DEFAULT_BASE_URL,
        api_key=api_key,
        timeout_ms=_int(env, "JARVIS_AI_TIMEOUT_MS", 30000),
        max_retries=_int(env, "JARVIS_AI_MAX_RETRIES", 2),
        fallback=(env.get("JARVIS_AI_FALLBACK") or "mock").strip().lower(),
    )


def build_ai_gateway(config: AIConfig | None = None) -> AIGateway:
    config = config or load_ai_config()

    # 1. Build Primary
    if config.provider == "gemini":
        from jarvis_core.ai_gateway import GeminiProvider

        primary = GeminiProvider(
            api_key=config.api_key or os.environ.get("GEMINI_API_KEY", "")
        )
    elif config.provider == "antigravity":
        from jarvis_core.ai_gateway import AntigravityCLIProvider

        primary = AntigravityCLIProvider()
    elif config.provider in {"openai", "openai-compatible"}:
        primary = OpenAICompatibleProvider(
            model=config.model or "gpt-4o",
            api_key=config.api_key or os.environ.get("OPENAI_API_KEY", ""),
            base_url=config.base_url,
            timeout_ms=config.timeout_ms,
            name=config.provider,
        )
    else:
        primary = MockAIProvider()

    # 2. Build Fallback
    fallback_provider = None
    if config.fallback == "openai":
        fallback_provider = OpenAICompatibleProvider(
            model="gpt-4o", api_key=os.environ.get("OPENAI_API_KEY", ""), name="openai"
        )
    elif config.fallback == "gemini":
        from jarvis_core.ai_gateway import GeminiProvider

        fallback_provider = GeminiProvider(api_key=os.environ.get("GEMINI_API_KEY", ""))
    elif config.fallback == "local-llama":
        from jarvis_core.ai_gateway import LocalLlamaProvider
        fallback_provider = LocalLlamaProvider(
            model=os.environ.get("JARVIS_LOCAL_AI_MODEL", "qwen3-1.7b-q4_k_m"),
            base_url=os.environ.get("JARVIS_LOCAL_AI_BASE_URL", "http://127.0.0.1:8081/v1"),
            timeout_ms=int(os.environ.get("JARVIS_LOCAL_TIMEOUT", "120000"))
        )
    elif config.fallback == "mock":
        fallback_provider = MockAIProvider()

    return AIGateway(
        primary=primary, fallback=fallback_provider, max_retries=config.max_retries
    )


def _int(env: Mapping[str, str], key: str, default: int) -> int:
    value = env.get(key)
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be an integer") from exc
