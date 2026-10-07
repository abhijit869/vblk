#!/bin/bash
set -e
ISO_PATH="/workspaces/vblk/dist/JARVIS-OS-1.0-amd64.iso"
echo "=== PHASE 5 FALLBACK: SQUASHFS INSPECTION ==="
sudo mkdir -p /mnt/iso /mnt/squashfs
sudo mount -o loop "$ISO_PATH" /mnt/iso
sudo mount -t squashfs -o loop /mnt/iso/live/filesystem.squashfs /mnt/squashfs

echo "Checking systemd paths:"
ls -ld /mnt/squashfs/var/log/jarvis || echo "MISSING /var/log/jarvis"
ls -ld /mnt/squashfs/var/lib/jarvis || echo "MISSING /var/lib/jarvis"

echo "Checking JARVIS user:"
cat /mnt/squashfs/etc/passwd | grep jarvis || true

sudo umount /mnt/squashfs
sudo umount /mnt/iso
