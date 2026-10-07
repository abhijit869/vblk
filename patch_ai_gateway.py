import re

with open("python/jarvis_core/ai_gateway.py", "r") as f:
    content = f.read()

# Replace complete in LocalLlamaProvider
old_complete = """    def complete(self, request: AIRequest) -> AIResponse:
        if not self._check_health():
            self._ensure_service_running()
        req = request
        if request.system_prompt == DEFAULT_SYSTEM_PROMPT:
            from dataclasses import replace
            req = replace(request, system_prompt=LOCAL_SYSTEM_PROMPT)
        return super().complete(req)"""

new_complete = """    def complete(self, request: AIRequest) -> AIResponse:
        import json
        from dataclasses import replace
        from jarvis_core.ai_gateway import AIToolCall
        if not self._check_health():
            self._ensure_service_running()
        
        req = request
        sys_prompt = LOCAL_SYSTEM_PROMPT if req.system_prompt == DEFAULT_SYSTEM_PROMPT else req.system_prompt
        
        if req.tools:
            tools_json = []
            for t in req.tools:
                tools_json.append({
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters
                })
            sys_prompt += "\\n\\n# Tools\\n\\nYou may call one or more functions to assist with the user query.\\n\\nYou are provided with function signatures within <tools></tools> XML tags:\\n<tools>\\n"
            sys_prompt += json.dumps(tools_json)
            sys_prompt += "\\n</tools>\\n\\nFor each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\\n<tool_call>\\n{\\"name\\": <function-name>, \\"arguments\\": <args-json-object>}\\n</tool_call>"
        
        req = replace(req, system_prompt=sys_prompt, tools=())
        
        res = super().complete(req)
        
        if not res.tool_calls and res.content:
            import re
            calls = re.findall(r"<tool_call>\\s*(\\{.*?\\})\\s*</tool_call>", res.content, re.DOTALL)
            parsed_calls = []
            for call_json in calls:
                try:
                    data = json.loads(call_json)
                    name = data.get("name")
                    args = data.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    if name:
                        parsed_calls.append(AIToolCall(tool=name, arguments=args))
                except json.JSONDecodeError:
                    pass
            if parsed_calls:
                res = replace(res, tool_calls=parsed_calls)
                
        return res"""

content = content.replace(old_complete, new_complete)

with open("python/jarvis_core/ai_gateway.py", "w") as f:
    f.write(content)

