#!/bin/bash
./dist/llama.cpp/llama-server -m downloads/models/Qwen3-1.7B-Q4_K_M.gguf --host 127.0.0.1 --port 8081 -c 2048 -t 2 -np 1 -ngl 0 > llama_server.log 2>&1 &
echo $! > llama_server.pid
echo "Started llama-server with PID $(cat llama_server.pid)"
