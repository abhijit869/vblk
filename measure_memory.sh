#!/bin/bash
set -e

PORT=8082
MODEL="downloads/models/Qwen3-1.7B-Q4_K_M.gguf"

function measure_run() {
    local ctx=$1
    echo "=== MEASURING WITH CONTEXT $ctx ==="
    
    # Start server in background
    ./dist/llama.cpp/llama-server -m "$MODEL" --host 127.0.0.1 --port $PORT -c $ctx -t 2 -np 1 -ngl 0 > llama_$ctx.log 2>&1 &
    local SERVER_PID=$!
    
    # Wait for startup
    sleep 5
    
    local IDLE_RSS=$(ps -o rss= -p $SERVER_PID | xargs)
    echo "Idle RSS (KB): $IDLE_RSS"
    
    # First inference
    echo "Running first inference..."
    curl -s -X POST http://127.0.0.1:$PORT/v1/chat/completions \
        -H "Content-Type: application/json" \
        -d '{"model": "Qwen3", "messages": [{"role": "user", "content": "Write a 500 word essay on the history of Linux."}]}' > /dev/null
        
    local INFERENCE_1_RSS=$(ps -o rss= -p $SERVER_PID | xargs)
    echo "First Inference Peak RSS (KB): $INFERENCE_1_RSS"
    
    # Second inference
    echo "Running second inference..."
    curl -s -X POST http://127.0.0.1:$PORT/v1/chat/completions \
        -H "Content-Type: application/json" \
        -d '{"model": "Qwen3", "messages": [{"role": "user", "content": "Write a 500 word essay on the history of AI."}]}' > /dev/null
        
    local INFERENCE_2_RSS=$(ps -o rss= -p $SERVER_PID | xargs)
    echo "Repeated Inference Peak RSS (KB): $INFERENCE_2_RSS"
    
    kill $SERVER_PID || true
    wait $SERVER_PID 2>/dev/null || true
}

measure_run 2048
sleep 2
measure_run 4096

