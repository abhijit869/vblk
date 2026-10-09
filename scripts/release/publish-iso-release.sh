#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ISO_PATH="${ISO_PATH:-$REPO_ROOT/dist/JARVIS-OS-1.0-amd64.iso}"
TAG="${1:-v1.0-iso}"
PART_SIZE="${PART_SIZE:-1900M}"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

command -v gh >/dev/null || {
    echo "ERROR: GitHub CLI (gh) is required." >&2
    exit 1
}
gh auth status >/dev/null 2>&1 || {
    echo "ERROR: authenticate first with: gh auth login" >&2
    exit 1
}
[ -f "$ISO_PATH" ] || {
    echo "ERROR: ISO not found: $ISO_PATH" >&2
    exit 1
}

BASE_NAME="$(basename "$ISO_PATH")"
split -d -a 2 -b "$PART_SIZE" "$ISO_PATH" "$WORK_DIR/$BASE_NAME.part-"
sha256sum "$ISO_PATH" > "$WORK_DIR/$BASE_NAME.sha256"
sha512sum "$ISO_PATH" > "$WORK_DIR/$BASE_NAME.sha512"
sha256sum "$WORK_DIR/$BASE_NAME.part-"* > "$WORK_DIR/$BASE_NAME.parts.sha256"

mapfile -t ASSETS < <(find "$WORK_DIR" -maxdepth 1 -type f -printf '%p\n' | sort)
if gh release view "$TAG" >/dev/null 2>&1; then
    gh release upload "$TAG" "${ASSETS[@]}" --clobber
else
    gh release create "$TAG" "${ASSETS[@]}" \
        --title "JARVIS OS 1.0" \
        --notes "JARVIS OS 1.0 ISO. Download all .part-* files and run scripts/release/download-iso.sh to reassemble and verify the ISO."
fi

echo "Release uploaded: $TAG"
