#!/bin/bash
set -e
echo "Guest RAM (Initial):"
free -h

echo "Starting model..."
sudo /usr/lib/jarvis/scripts/local-ai-lifecycle.sh start || systemctl start jarvis-local-ai.service
sleep 5

echo "Guest RAM (Loaded):"
free -h

echo "Sending inference request..."
curl -s http://127.0.0.1:8081/v1/chat/completions -H "Content-Type: application/json" -d '{
  "model": "qwen3-1.7b-q4_k_m",
  "messages": [{"role": "user", "content": "What is 2+2?"}]
}' > /dev/null &
PID=$!
sleep 2

echo "Guest RAM (Inference Peak):"
free -h
wait $PID

echo "Memory Test Complete."
