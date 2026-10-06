#!/bin/bash
ISO_PATH="/workspaces/vblk/dist/JARVIS-OS-1.0-amd64.iso"
echo "=== PHASE 4: QEMU UEFI SECURE BOOT ON ==="
cp /usr/share/OVMF/OVMF_VARS_4M.ms.fd /tmp/vars_on.fd
qemu-system-x86_64 -m 2048 -machine q35 \
  -drive if=pflash,format=raw,unit=0,file=/usr/share/OVMF/OVMF_CODE_4M.secboot.fd,readonly=on \
  -drive if=pflash,format=raw,unit=1,file=/tmp/vars_on.fd \
  -cdrom "$ISO_PATH" -boot d -display none -qmp tcp:localhost:4444,server,nowait &
QEMU_PID=$!
sleep 25
echo -e '{"execute": "qmp_capabilities"}\n{"execute": "screendump", "arguments": {"filename": "/workspaces/vblk/reports/uefi_on_boot.ppm"}}' | nc localhost 4444 || true
kill $QEMU_PID
convert /workspaces/vblk/reports/uefi_on_boot.ppm /workspaces/vblk/reports/uefi_on_boot.png || true
echo "UEFI (SB ON) Boot screenshot saved to reports/uefi_on_boot.png"
