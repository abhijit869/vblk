#!/bin/bash
for ctx in 2048 4096; do
    echo "--- CONTEXT $ctx ---"
    grep "model size" llama_$ctx.log || true
    grep "KV self size" llama_$ctx.log || true
    grep "compute buffer size" llama_$ctx.log || true
done
