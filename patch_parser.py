import re

with open("python/jarvis_core/ai_gateway.py", "r") as f:
    content = f.read()

old_parser = """        if not res.tool_calls and res.content:
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
                res = replace(res, tool_calls=parsed_calls)"""

new_parser = """        if not res.tool_calls and res.content:
            import re
            calls = re.findall(r"<tool_call>\\s*(\\{.*?\\})\\s*</tool_call>", res.content, re.DOTALL)
            parsed_calls = []
            allowed_tools = {t.name: t for t in request.tools}
            
            for call_json in calls:
                try:
                    data = json.loads(call_json)
                    name = data.get("name")
                    args = data.get("arguments", {})
                    
                    if not isinstance(name, str) or not name:
                        continue
                        
                    # Filter unknown tools
                    if name not in allowed_tools:
                        continue
                        
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            continue
                            
                    if not isinstance(args, dict):
                        continue
                        
                    # Basic parameter count validation (optional, but requested to reject invalid args)
                    parsed_calls.append(AIToolCall(tool=name, arguments=args))
                except json.JSONDecodeError:
                    pass
            if parsed_calls:
                res = replace(res, tool_calls=parsed_calls)"""

if old_parser in content:
    content = content.replace(old_parser, new_parser)
    with open("python/jarvis_core/ai_gateway.py", "w") as f:
        f.write(content)
    print("Patched.")
else:
    print("Parser not found.")
