#!/bin/bash
set -e

echo "Running Documentation Consistency Check..."
ERRORS=0

function check_term() {
    local term="$1"
    local error_msg="$2"
    local files=$(find . -type f -name "*.md" -not -path "./.git/*" -not -path "./node_modules/*" -not -path "./downloads/*" -exec grep -Hn -i "$term" {} \;)
    if [ ! -z "$files" ]; then
        echo "ERROR: Found forbidden term '$term': $error_msg"
        echo "$files"
        ERRORS=$((ERRORS+1))
    fi
}

check_term "Qwen2\.5" "Qwen2.5 is not the production model (unless marked as INVALID/historical). (You may need to manually verify this if historical)."
check_term "v3901" "v3901 is rejected. Pinned version is b11429. (Manual verify if marked as historical)."
check_term "Debian 13 (Bookworm)" "Bookworm is Debian 12, not Debian 13."
check_term "VMware PASS" "VMware is BLOCKED, not PASS."
check_term "VMware: PASS" "VMware is BLOCKED, not PASS."
check_term "2048 layers" "Use 2048-token context, not layers."
check_term "4096 PASS" "4096 test is IN PROGRESS."
check_term "2 GB PASS" "2 GB VM complete guest test is NOT PROVEN."
check_term "FINAL ISO BUILD PASS" "Final ISO build is IN PROGRESS."

if [ $ERRORS -gt 0 ]; then
    echo "Consistency check failed with $ERRORS rules violated."
    exit 1
else
    echo "Consistency check passed!"
    exit 0
fi
