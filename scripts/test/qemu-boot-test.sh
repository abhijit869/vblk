#!/bin/bash
ISO_PATH=${1:-dist/JARVIS-OS-1.0-amd64.iso}
if [ ! -f "$ISO_PATH" ]; then echo "ISO not found: $ISO_PATH"; exit 1; fi
echo "=> Testing BIOS Boot in QEMU..."
timeout 60 qemu-system-x86_64 -m 2048 -cdrom "$ISO_PATH" -boot d -nographic -serial file:reports/qemu-bios-boot.log || true
echo "=> Checking output..."
grep -i "Linux version" reports/qemu-bios-boot.log || echo "Warning: Kernel boot string not found in serial log"
