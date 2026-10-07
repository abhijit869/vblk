#!/bin/bash
./dist/llama.cpp/llama-server --help | grep -E "reasoning|reasoning-format" || echo "No reasoning flags found."
