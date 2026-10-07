#!/bin/bash
set -e
echo "=> Cleaning JARVIS OS Build Environment..."
sudo pkill -9 -f "lb build" || true
sudo umount -l /tmp/jarvis_build/iso/chroot/proc 2>/dev/null || true
sudo umount -l /tmp/jarvis_build/iso/chroot/sys 2>/dev/null || true
sudo rm -rf /tmp/jarvis_build
echo "=> Clean Complete."
