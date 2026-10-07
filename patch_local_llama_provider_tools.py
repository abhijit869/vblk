import re

with open("python/jarvis_core/ai_gateway.py", "r") as f:
    content = f.read()

# I will replace the complete and respond methods of LocalLlamaProvider
new_methods = """
    def complete(self, request: AIRequest) -> AIResponse:
        import json
        if not self._check_health():
            self._ensure_service_running()
        
        req = request
        sys_prompt = LOCAL_SYSTEM_PROMPT if req.system_prompt == DEFAULT_SYSTEM_PROMPT else req.system_prompt
        
        if req.tools:
            # Manually inject tools into system prompt
            tools_json = []
            for t in req.tools:
                tools_json.append({
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters
                })
            sys_prompt += "\\n\\nYou have access to the following tools:\\n" + json.dumps(tools_json, indent=2)
            sys_prompt += "\\nTo call a tool, output a JSON object like:\\n{\\"tool_calls\\": [{\\"name\\": \\"tool_name\\", \\"arguments\\": {\\"arg\\": \\"value\\"}}]}"
        
        from dataclasses import replace
        # Remove tools from the request we send to super so it doesn't pass 'tools' to llama.cpp
        req = replace(req, system_prompt=sys_prompt, tools=())
        
        res = super().complete(req)
        
        # Manually parse tool calls from response if any
        if not res.tool_calls and res.content:
            try:
                # Try to find JSON block
                import re
                match = re.search(r'\\{.*?\\"tool_calls\\".*?\\}', res.content, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    if "tool_calls" in data:
                        parsed_calls = []
                        for tc in data["tool_calls"]:
                            from jarvis_core.ai_gateway import AIToolCall
                            parsed_calls.append(AIToolCall(tool=tc.get("name", tc.get("tool", "")), arguments=tc.get("arguments", {})))
                        res = replace(res, tool_calls=parsed_calls)
            except Exception:
                pass
                
        return res

    def respond(self, request: AIRequest, outputs: Sequence[AIToolOutput]) -> AIResponse:
        if not self._check_health():
            self._ensure_service_running()
        req = request
        if request.system_prompt == DEFAULT_SYSTEM_PROMPT:
            from dataclasses import replace
            req = replace(request, system_prompt=LOCAL_SYSTEM_PROMPT)
        # Just use super without tools for respond
        req = replace(req, tools=())
        return super().respond(req, outputs)
"""

content = re.sub(
    r"    def complete\(self, request: AIRequest\) -> AIResponse:.*?return super\(\)\.respond\(req, outputs\)",
    new_methods.strip(),
    content,
    flags=re.DOTALL
)

with open("python/jarvis_core/ai_gateway.py", "w") as f:
    f.write(content)

