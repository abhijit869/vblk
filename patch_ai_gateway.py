import re

with open("python/jarvis_core/ai_gateway.py", "r") as f:
    content = f.read()

# Add LocalLlamaProvider
local_provider_code = """
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

    def health(self) -> ProviderHealth:
        # Check /v1/models endpoint
        import urllib.request
        import json
        import urllib.error
        req = urllib.request.Request(self._base_url + "/models", method="GET")
        try:
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read())
                    # Check if our model is loaded
                    return ProviderHealth(self.name, ProviderStatus.HEALTHY)
        except Exception as e:
            return ProviderHealth(self.name, ProviderStatus.UNAVAILABLE, f"Local AI unavailable: {e}")
        return ProviderHealth(self.name, ProviderStatus.UNAVAILABLE, "Unknown error")
"""

if "class LocalLlamaProvider" not in content:
    content = content + "\n\n" + local_provider_code

with open("python/jarvis_core/ai_gateway.py", "w") as f:
    f.write(content)

