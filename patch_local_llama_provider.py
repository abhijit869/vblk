import re

with open("python/jarvis_core/ai_gateway.py", "r") as f:
    content = f.read()

new_local_provider = """
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
        # Try to start it using the helper
        try:
            subprocess.run(
                ["sudo", "/usr/lib/jarvis/scripts/local-ai-lifecycle.sh", "start"],
                check=True, capture_output=True
            )
            # Wait for it to be healthy
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
        return super().complete(request)

    def respond(self, request: AIRequest, outputs: Sequence[AIToolOutput]) -> AIResponse:
        if not self._check_health():
            self._ensure_service_running()
        return super().respond(request, outputs)
"""

# Replace the existing class we inserted
pattern = re.compile(r"class LocalLlamaProvider\(OpenAICompatibleProvider\):.*?return ProviderHealth\(self\.name, ProviderStatus\.UNAVAILABLE, \"Unknown error\"\)", re.DOTALL)
content = pattern.sub(new_local_provider.strip(), content)

with open("python/jarvis_core/ai_gateway.py", "w") as f:
    f.write(content)

