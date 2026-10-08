#!/bin/bash
set -e
echo "=> Running JARVIS OS Preflight Checks..."
[ "$EUID" -eq 0 ] || { echo "Must run as root"; exit 1; }
command -v lb >/dev/null || { echo "live-build is required"; exit 1; }
command -v debootstrap >/dev/null || { echo "debootstrap required"; exit 1; }
command -v mksquashfs >/dev/null || { echo "squashfs-tools required"; exit 1; }
command -v xorriso >/dev/null || { echo "xorriso required"; exit 1; }
FREE_MEM=$(free -m | awk '/^Mem:/{print $7}')
if [ "$FREE_MEM" -lt 2048 ]; then echo "Warning: Less than 2GB free RAM"; fi
echo "=> Preflight PASS"
