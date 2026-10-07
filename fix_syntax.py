with open("python/jarvis_core/ai_gateway.py", "r") as f:
    content = f.read()

content = content.replace(")\\n\\nDEFAULT_SYSTEM_PROMPT = (", ")\n\nDEFAULT_SYSTEM_PROMPT = (")

with open("python/jarvis_core/ai_gateway.py", "w") as f:
    f.write(content)
