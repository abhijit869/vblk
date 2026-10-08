#!/bin/bash
set -e
apt-get update -qq

FAIL=0
grep -v "^#" iso/config/package-lists/jarvis.list.chroot | grep -v "^$" | while read pkg; do
    if ! apt-cache policy "$pkg" 2>/dev/null | grep -q "Candidate:"; then
        echo "FAIL: Package not found: $pkg"
        FAIL=1
    fi
done
exit $FAIL
