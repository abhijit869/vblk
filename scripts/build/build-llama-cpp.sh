#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
source "$REPO_ROOT/config/local-ai/llama-cpp-version.env"

BUILD_DIR="$REPO_ROOT/downloads/llama.cpp"
DIST_DIR="$REPO_ROOT/dist/llama.cpp"

if [ ! -d "$BUILD_DIR" ]; then
    git clone "$LLAMA_CPP_REPO" "$BUILD_DIR"
fi

cd "$BUILD_DIR"
git fetch origin
git checkout "$LLAMA_CPP_VERSION"

if [ -n "${LLAMA_CPP_COMMIT:-}" ]; then
    CURRENT_COMMIT=$(git rev-parse HEAD)
    if [ "$CURRENT_COMMIT" != "$LLAMA_CPP_COMMIT" ]; then
        echo "ERROR: Checked out commit $CURRENT_COMMIT does not match expected $LLAMA_CPP_COMMIT"
        exit 1
    fi
fi

mkdir -p build
cd build

cmake .. -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DGGML_METAL=OFF -DGGML_NATIVE=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release -j2 --target llama-server

mkdir -p "$DIST_DIR"
cp -a bin/llama-server bin/lib*.so* "$DIST_DIR/"

echo "llama.cpp CPU runtime built successfully."
