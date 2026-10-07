import re

with open("python/jarvis_core/ai_gateway.py", "r") as f:
    content = f.read()

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

if "LOCAL_SYSTEM_PROMPT =" not in content:
    content = content.replace("DEFAULT_SYSTEM_PROMPT =", local_prompt.strip() + "\n\nDEFAULT_SYSTEM_PROMPT =")

# Update LocalLlamaProvider to inject this prompt if not already overridden
# The `request.system_prompt` might be `DEFAULT_SYSTEM_PROMPT`, we need to replace it.
override_code = """
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

content = re.sub(
    r"    def complete\(self, request: AIRequest\) -> AIResponse:.*?return super\(\)\.respond\(request, outputs\)",
    override_code.strip(),
    content,
    flags=re.DOTALL
)

with open("python/jarvis_core/ai_gateway.py", "w") as f:
    f.write(content)
