#!/bin/bash
ISO_PATH="/workspaces/vblk/dist/JARVIS-OS-1.0-amd64.iso"
echo "=== PHASE 2: QEMU BIOS BOOT ==="
qemu-system-x86_64 -m 2048 -cdrom "$ISO_PATH" -boot d -display none -qmp tcp:localhost:4444,server,nowait &
QEMU_PID=$!
sleep 25
echo -e '{"execute": "qmp_capabilities"}\n{"execute": "screendump", "arguments": {"filename": "/workspaces/vblk/reports/bios_boot.ppm"}}' | nc localhost 4444 || true
kill $QEMU_PID
convert /workspaces/vblk/reports/bios_boot.ppm /workspaces/vblk/reports/bios_boot.png || true
echo "BIOS Boot screenshot saved to reports/bios_boot.png"
