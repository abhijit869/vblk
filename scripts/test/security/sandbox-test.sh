#!/bin/bash
set -e
echo "=> Starting JARVIS Sandbox Audit..."
if ! command -v bwrap >/dev/null 2>&1; then
    echo "FAIL: bubblewrap (bwrap) is not installed."
    exit 1
fi
echo "Testing bwrap isolation..."
bwrap --ro-bind / / --unshare-all --uid 1000 --gid 1000 -- ls / >/dev/null
echo "PASS: Bubblewrap executes successfully."
exit 0
