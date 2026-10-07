with open("python/jarvis_core/ai_gateway.py", "r") as f:
    content = f.read()

import re
broken = re.search(r"                match = re\.search.*?pass", content, re.DOTALL)
if broken:
    new_parsing = r"""                # Try to parse the whole content as JSON or extract the block
                text = res.content.strip('`\n"\' ')
                if text.startswith('```json'):
                    text = text[7:]
                text = text.strip('`\n"\' ')
                
                # If there's extra text, try to find the start of the object
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
                    res = replace(res, tool_calls=parsed_calls)"""
    content = content[:broken.start()] + new_parsing + content[broken.end():]

with open("python/jarvis_core/ai_gateway.py", "w") as f:
    f.write(content)
