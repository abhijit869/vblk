#!/bin/bash
curl -s -X POST http://127.0.0.1:8081/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen3",
    "messages": [
      {"role": "user", "content": "Check the current CPU usage."}
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "system.cpu",
          "description": "Get current CPU usage",
          "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": false
          }
        }
      }
    ]
  }'
