import sys
import json
from jarvis_core.ai_gateway import LocalLlamaProvider, AIRequest, AIToolSpec, ProviderStatus

def main():
    print("Testing Tool Calling...")
    tools = (
        AIToolSpec("system.cpu", "Get CPU usage", {"type": "object", "properties": {}}),
    )
    provider = LocalLlamaProvider(base_url="http://127.0.0.1:8081/v1")
    req = AIRequest(prompt="Check the current CPU usage.", tools=tools)
    
    print("Sending request to LocalLlamaProvider...")
    res = provider.complete(req)
    
    print("\n[Raw Content]")
    print(res.content)
    
    print("\n[Parsed Tools]")
    for tc in res.tool_calls:
        print(f"Tool: {tc.tool}, Args: {tc.arguments}")
        
    if res.tool_calls and res.tool_calls[0].tool == "system.cpu":
        print("PASS")
    else:
        print("FAIL: Expected system.cpu to be called")

if __name__ == "__main__":
    main()
