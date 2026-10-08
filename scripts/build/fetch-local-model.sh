#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
source "$REPO_ROOT/config/local-ai/model.env"

CACHE_DIR="$REPO_ROOT/downloads/models"
OUT_FILE="$CACHE_DIR/$MODEL_TARGET_NAME"

mkdir -p "$CACHE_DIR"

if [ -f "$OUT_FILE" ]; then
    echo "Model already exists at $OUT_FILE"
else
    MODEL_URL="https://huggingface.co/${MODEL_REPO}/resolve/${MODEL_REVISION}/${MODEL_FILENAME}"
    echo "Downloading $MODEL_TARGET_NAME from $MODEL_URL ..."
    curl -L -o "$OUT_FILE" "$MODEL_URL"
    echo "Download complete."
fi

echo "Verifying SHA256..."
REAL_SHA=$(sha256sum "$OUT_FILE" | awk '{print $1}')
echo "REAL SHA256: $REAL_SHA"

# Update model.env with the real SHA256 so the build uses it
sed -i "s/^MODEL_SHA256=.*/MODEL_SHA256=$REAL_SHA/" "$REPO_ROOT/config/local-ai/model.env"

echo "Model verified successfully."
