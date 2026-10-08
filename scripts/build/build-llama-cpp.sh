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

echo "Building llama.cpp in debian:bookworm container to match ISO glibc..."
# Cache check logic: If target binary exists and we haven't modified source, we could skip cmake, but the prompt says:
# "Cache hit and cache miss must execute the same staging logic." So we just run cmake --build (which is cached)
docker run --rm \
    -v "$BUILD_DIR:/src" \
    -w /src/build \
    debian:bookworm bash -c "apt-get update && apt-get install -y build-essential cmake git && cmake .. -DGGML_CUDA=OFF -DGGML_VULKAN=OFF -DGGML_METAL=OFF -DGGML_NATIVE=OFF -DGGML_AVX=OFF -DGGML_AVX2=OFF -DGGML_FMA=OFF -DGGML_F16C=OFF -DCMAKE_BUILD_TYPE=Release && cmake --build . --config Release -j\$(nproc) --target llama-server && chown -R $(id -u):$(id -g) /src/build"

mkdir -p "$DIST_DIR"
cp -a bin/llama-server bin/lib*.so* "$DIST_DIR/"
chmod 755 "$DIST_DIR"/llama-server "$DIST_DIR"/lib*.so*

# Permission normalization and check
if [ ! -x "$DIST_DIR/llama-server" ]; then
    echo "ERROR: llama-server is not executable!"
    exit 1
fi

echo "Verifying GLIBC ABI compatibility (TARGET: Debian Bookworm / GLIBC <= 2.36)..."
for bin in "$DIST_DIR/llama-server" "$DIST_DIR"/lib*.so*; do
    if objdump -T "$bin" 2>/dev/null | grep -qE 'GLIBC_2\.(3[7-9]|[4-9][0-9])'; then
        echo "ERROR: $bin requires an unsupported GLIBC version! (Found > 2.36)"
        objdump -T "$bin" | grep -E 'GLIBC_2\.(3[7-9]|[4-9][0-9])'
        exit 1
    fi
done
echo "GLIBC ABI verification passed."

echo "Verifying CPU/ISA compatibility..."
if objdump -d "$DIST_DIR/llama-server" | grep -qE 'vfmadd|vaddps %ymm|vmovups %ymm'; then
    echo "ERROR: AVX/AVX2/FMA instructions found in binary, portability violation!"
    exit 1
fi
echo "CPU/ISA compatibility passed."

echo "Verifying shared library dependencies..."
if ! ldd "$DIST_DIR/llama-server" > /dev/null; then
    echo "ERROR: Failed to resolve shared dependencies for llama-server"
    exit 1
fi

echo "Recording SHA256 values..."
cd "$DIST_DIR"
sha256sum llama-server lib*.so* > SHA256SUMS
cat SHA256SUMS

echo "llama.cpp CPU runtime built successfully and strictly verified."
