import os
import sys
from jarvis_core.config import build_ai_gateway, AIConfig
from jarvis_core.ai_gateway import AIRequest

providers = ["antigravity", "gemini", "openai"]
print("Testing JARVIS Core Brain Providers...\n")

for provider in providers:
    print(f"--- Testing {provider.upper()} ---")
    
    api_key = None
    if provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY", "")
    elif provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
    
    if provider in ["gemini", "openai"] and not api_key:
        print(f"FAIL: {provider.upper()}_API_KEY is missing from environment.")
        continue
        
    config = AIConfig(provider=provider, api_key=api_key, fallback="none")
    gateway = build_ai_gateway(config)
    
    req = AIRequest(prompt="Say exactly: HELLO JARVIS", system_prompt="You are an AI.")
    try:
        response = gateway.complete(req)
        print(f"SUCCESS! Response: {response.content.strip()}")
    except Exception as e:
        print(f"FAIL! Error: {e}")
    print()
