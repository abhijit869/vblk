with open("python/jarvis_core/ai_gateway.py", "r") as f:
    content = f.read()

content = content.replace("request.system_prompt + \"\n\n\" + cmd[-1]", "request.system_prompt + \"\\n\\n\" + cmd[-1]")

with open("python/jarvis_core/ai_gateway.py", "w") as f:
    f.write(content)
