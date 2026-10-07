with open("python/jarvis_core/ai_gateway.py", "r") as f:
    content = f.read()

# I will replace the complete method in LocalLlamaProvider to just set the system prompt, but NOT clear the tools array.

import re

# Match the old complete method in LocalLlamaProvider
pattern = r"    def complete\(self, request: AIRequest\) -> AIResponse:.*?    def respond\("
replacement = """    def complete(self, request: AIRequest) -> AIResponse:
        from dataclasses import replace
        if not self._check_health():
            self._ensure_service_running()
        
        req = request
        if req.system_prompt == DEFAULT_SYSTEM_PROMPT:
            req = replace(req, system_prompt=LOCAL_SYSTEM_PROMPT)
            
        return super().complete(req)

    def respond("""

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open("python/jarvis_core/ai_gateway.py", "w") as f:
    f.write(new_content)
print("Patched LocalLlamaProvider")
