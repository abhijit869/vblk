with open("python/jarvis_core/ai_gateway.py", "r") as f:
    c = f.read()

old_code = """            try:
                import re
                match = re.search(r'\\{.*?"tool_calls".*?\\}', res.content, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    if "tool_calls" in data:
                        parsed_calls = []
                        for tc in data["tool_calls"]:
                            from jarvis_core.ai_gateway import AIToolCall
                            parsed_calls.append(AIToolCall(tool=tc.get("name", tc.get("tool", "")), arguments=tc.get("arguments", {})))
                        res = replace(res, tool_calls=parsed_calls)
            except Exception:
                pass"""

new_code = """            try:
                text = res.content.strip('`\\n"\\' ')
                if text.startswith('```json'):
                    text = text[7:].strip('`\\n"\\' ')
                start = text.find('{')
                end = text.rfind('}')
                if start != -1 and end != -1:
                    text = text[start:end+1]
                data = json.loads(text)
                if "tool_calls" in data:
                    parsed_calls = []
                    for tc in data["tool_calls"]:
                        from jarvis_core.ai_gateway import AIToolCall
                        parsed_calls.append(AIToolCall(tool=tc.get("name", tc.get("tool", "")), arguments=tc.get("arguments", {})))
                    res = replace(res, tool_calls=parsed_calls)
            except Exception:
                pass"""

c = c.replace(old_code, new_code)
with open("python/jarvis_core/ai_gateway.py", "w") as f:
    f.write(c)
