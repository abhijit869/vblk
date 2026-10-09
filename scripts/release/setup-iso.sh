#!/usr/bin/env bash
set -euo pipefail

REPO="${REPO:-abhijit869/vblk}"
TAG="${1:-v1.0-iso}"
OUTPUT_DIR="${2:-.}"
BASE_NAME="${ISO_NAME:-JARVIS-OS-1.0-amd64.iso}"
RELEASE_URL="https://github.com/$REPO/releases/download/$TAG"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

command -v curl >/dev/null || {
    echo "ERROR: curl is required." >&2
    exit 1
}
command -v sha256sum >/dev/null || {
    echo "ERROR: sha256sum is required." >&2
    exit 1
}
mkdir -p "$OUTPUT_DIR"

MANIFEST="$WORK_DIR/$BASE_NAME.parts.sha256"
curl --fail --location --retry 3 --output "$MANIFEST" \
    "$RELEASE_URL/$BASE_NAME.parts.sha256"
awk '{ path = $2; sub(".*/", "", path); print $1 "  " path }' \
    "$MANIFEST" > "$MANIFEST.normalized"
mv "$MANIFEST.normalized" "$MANIFEST"

mapfile -t PARTS < <(awk '{print $2}' "$MANIFEST" | sort)
(( ${#PARTS[@]} > 0 )) || {
    echo "ERROR: no ISO parts found in checksum manifest." >&2
    exit 1
}

for part in "${PARTS[@]}"; do
    case "$part" in
        "$BASE_NAME".part-*) ;;
        *)
            echo "ERROR: unexpected file in checksum manifest: $part" >&2
            exit 1
            ;;
    esac
    curl --fail --location --retry 3 --output "$WORK_DIR/$part" \
        "$RELEASE_URL/$part"
done

(cd "$WORK_DIR" && sha256sum --check "$MANIFEST")
cat "${PARTS[@]/#/$WORK_DIR/}" > "$OUTPUT_DIR/$BASE_NAME"

curl --fail --location --retry 3 --output "$WORK_DIR/$BASE_NAME.sha256" \
    "$RELEASE_URL/$BASE_NAME.sha256"
awk '{ path = $2; sub(".*/", "", path); print $1 "  " path }' \
    "$WORK_DIR/$BASE_NAME.sha256" > "$WORK_DIR/$BASE_NAME.sha256.normalized"
(cd "$OUTPUT_DIR" && sha256sum --check "$WORK_DIR/$BASE_NAME.sha256.normalized")
echo "ISO restored and verified: $OUTPUT_DIR/$BASE_NAME"
