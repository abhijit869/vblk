#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TAG="${1:-v1.0-iso}"
OUTPUT_DIR="${2:-$REPO_ROOT/dist}"
BASE_NAME="${ISO_NAME:-JARVIS-OS-1.0-amd64.iso}"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

command -v gh >/dev/null || {
    echo "ERROR: GitHub CLI (gh) is required." >&2
    exit 1
}
mkdir -p "$OUTPUT_DIR"
gh release download "$TAG" --repo abhijit869/vblk \
    --pattern "$BASE_NAME.part-*" --dir "$WORK_DIR"

shopt -s nullglob
parts=("$WORK_DIR"/"$BASE_NAME".part-*)
(( ${#parts[@]} > 0 )) || {
    echo "ERROR: no ISO parts found in release $TAG" >&2
    exit 1
}
IFS=$'\n' parts=($(printf '%s\n' "${parts[@]}" | sort))
cat "${parts[@]}" > "$OUTPUT_DIR/$BASE_NAME"

gh release download "$TAG" --repo abhijit869/vblk \
    --pattern "$BASE_NAME.sha256" --dir "$WORK_DIR"
(cd "$OUTPUT_DIR" && sha256sum -c "$WORK_DIR/$BASE_NAME.sha256")
echo "ISO restored and verified: $OUTPUT_DIR/$BASE_NAME"
