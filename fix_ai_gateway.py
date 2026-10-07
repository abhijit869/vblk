import re

with open("python/jarvis_core/ai_gateway.py", "r") as f:
    content = f.read()

# 1. System Prompt
local_prompt = """
LOCAL_SYSTEM_PROMPT = (
    "You are the emergency local reasoning brain of JARVIS OS.\\n"
    "1. The operating system is Debian-based JARVIS OS.\\n"
    "2. You control the OS ONLY through registered JARVIS tools.\\n"
    "3. Never invent tool results.\\n"
    "4. Never claim an operation succeeded without verification.\\n"
    "5. Inspect system state before changing it.\\n"
    "6. Prefer deterministic tools over guesses.\\n"
    "7. For failures: DETECT -> DIAGNOSE -> PLAN -> AUTHORIZE -> REPAIR -> VERIFY\\n"
    "8. If verification fails: collect new evidence -> revise diagnosis -> attempt a safer alternative\\n"
    "9. Never use unrestricted shell access.\\n"
    "10. Never bypass JARVIS Policy Engine.\\n"
    "11. Never expose secrets.\\n"
    "12. Never reveal API keys.\\n"
    "13. Never modify protected system areas without authorization.\\n"
    "14. Never perform destructive operations automatically unless explicitly allowed by policy.\\n"
    "15. When uncertain, gather evidence.\\n"
    "16. Report exact errors when known.\\n"
    "17. Do not pretend to know facts unavailable through tools.\\n"
    "18. Keep CPU/memory usage reasonable.\\n"
    "19. Prefer small tool calls and focused diagnostics.\\n"
    "20. Always verify repairs."
)
"""

content = content.replace("DEFAULT_SYSTEM_PROMPT = (", local_prompt.strip() + "\\n\\nDEFAULT_SYSTEM_PROMPT = (")

# 2. Add LocalLlamaProvider at the end
local_provider = """
class LocalLlamaProvider(OpenAICompatibleProvider):
    \"\"\"Local emergency fallback using llama.cpp.\"\"\"

    name = "local-llama"

    def __init__(
        self,
        model: str = "qwen3-1.7b-q4_k_m",
        base_url: str = "http://127.0.0.1:8081/v1",
        timeout_ms: int = 120000,
    ) -> None:
        super().__init__(model=model, base_url=base_url, timeout_ms=timeout_ms, name=self.name)

    def _ensure_service_running(self) -> None:
        import subprocess
        import time
        try:
            subprocess.run(
                ["sudo", "/usr/lib/jarvis/scripts/local-ai-lifecycle.sh", "start"],
                check=True, capture_output=True
            )
            for _ in range(30):
                if self._check_health():
                    return
                time.sleep(1)
        except Exception:
            pass

    def _check_health(self) -> bool:
        import urllib.request
        import json
        req = urllib.request.Request(self._base_url + "/models", method="GET")
        try:
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def health(self) -> ProviderHealth:
        if self._check_health():
            return ProviderHealth(self.name, ProviderStatus.HEALTHY)
        return ProviderHealth(self.name, ProviderStatus.UNAVAILABLE, "Local AI not running")

    def complete(self, request: AIRequest) -> AIResponse:
        if not self._check_health():
            self._ensure_service_running()
        req = request
        if request.system_prompt == DEFAULT_SYSTEM_PROMPT:
            from dataclasses import replace
            req = replace(request, system_prompt=LOCAL_SYSTEM_PROMPT)
        return super().complete(req)

    def respond(self, request: AIRequest, outputs: Sequence[AIToolOutput]) -> AIResponse:
        if not self._check_health():
            self._ensure_service_running()
        req = request
        if request.system_prompt == DEFAULT_SYSTEM_PROMPT:
            from dataclasses import replace
            req = replace(request, system_prompt=LOCAL_SYSTEM_PROMPT)
        return super().respond(req, outputs)
"""
content += "\\n\\n" + local_provider

# 3. Patch AIGateway for circuit breaker
orig_gateway = """class AIGateway:
    \"\"\"Routes requests to the primary provider with retry, then to a fallback.\"\"\"

    def __init__(
        self,
        primary: AIProvider | None = None,
        fallback: AIProvider | None = None,
        max_retries: int = 2,
        backoff_s: float = 0.5,
        max_backoff_s: float = 8.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._primary = primary or MockAIProvider()
        self._fallback = fallback
        self._max_retries = max(0, max_retries)
        self._backoff_s = backoff_s
        self._max_backoff_s = max_backoff_s
        self._sleep = sleep"""

new_gateway = """class AIGateway:
    \"\"\"Routes requests to the primary provider with retry, then to a fallback.\"\"\"

    def __init__(
        self,
        primary: AIProvider | None = None,
        fallback: AIProvider | None = None,
        max_retries: int = 2,
        backoff_s: float = 0.5,
        max_backoff_s: float = 8.0,
        sleep: Callable[[float], None] = time.sleep,
        failure_threshold: int = 2,
        recovery_threshold: int = 3,
    ) -> None:
        self._primary = primary or MockAIProvider()
        self._fallback = fallback
        self._max_retries = max(0, max_retries)
        self._backoff_s = backoff_s
        self._max_backoff_s = max_backoff_s
        self._sleep = sleep
        
        self._failure_threshold = failure_threshold
        self._recovery_threshold = recovery_threshold
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._circuit_open = False"""

content = content.replace(orig_gateway, new_gateway)

# Patch health
orig_health = """    def health(self) -> ProviderHealth:
        return self._primary.health()"""

new_health = """    def health(self) -> ProviderHealth:
        if self._circuit_open:
            h = self._primary.health()
            if h.status == ProviderStatus.HEALTHY:
                self._consecutive_successes += 1
                if self._consecutive_successes >= self._recovery_threshold:
                    self._circuit_open = False
                    self._consecutive_failures = 0
                    self._consecutive_successes = 0
            else:
                self._consecutive_successes = 0
            
            if self._circuit_open and self._fallback:
                return self._fallback.health()

        h = self._primary.health()
        if h.status == ProviderStatus.UNAVAILABLE and self._fallback:
            return self._fallback.health()
        return h"""

content = content.replace(orig_health, new_health)

# Patch _route
orig_route = """    def _route(
        self, request: AIRequest, call: Callable[[AIProvider], AIResponse]
    ) -> AIResponse:
        health = self._primary.health()
        if health.status == ProviderStatus.UNAVAILABLE:
            reason = health.message or "AI provider unavailable"
            return self._use_fallback(request, call, reason)

        try:
            return self._with_retry(self._primary, call)
        except ProviderError as exc:
            return self._use_fallback(request, call, str(exc))"""

new_route = """    def _route(
        self, request: AIRequest, call: Callable[[AIProvider], AIResponse]
    ) -> AIResponse:
        self.health()
        
        if self._circuit_open:
            return self._use_fallback(request, call, "Circuit breaker open")

        health = self._primary.health()
        if health.status == ProviderStatus.UNAVAILABLE:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._failure_threshold:
                self._circuit_open = True
            reason = health.message or "AI provider unavailable"
            return self._use_fallback(request, call, reason)

        try:
            res = self._with_retry(self._primary, call)
            self._consecutive_failures = 0
            return res
        except ProviderError as exc:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._failure_threshold:
                self._circuit_open = True
            return self._use_fallback(request, call, str(exc))"""

content = content.replace(orig_route, new_route)

with open("python/jarvis_core/ai_gateway.py", "w") as f:
    f.write(content)
