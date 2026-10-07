#!/bin/bash
set -e
ISO_PATH="/workspaces/vblk/dist/JARVIS-OS-1.0-amd64.iso"
echo "=== PHASE 1: STATIC ISO VALIDATION ==="
file "$ISO_PATH"
ls -lh "$ISO_PATH"
sha256sum "$ISO_PATH"
sha512sum "$ISO_PATH"
xorriso -indev "$ISO_PATH" -toc 2>/dev/null || true
xorriso -indev "$ISO_PATH" -report_el_torito as_mkisofs 2>/dev/null || true
echo "--- Finding EFI/Boot files ---"
xorriso -indev "$ISO_PATH" -find / -name "*.efi" -print 2>/dev/null || true
xorriso -indev "$ISO_PATH" -find / -name "BOOTX64.EFI" -print 2>/dev/null || true
xorriso -indev "$ISO_PATH" -find / -name "grubx64.efi" -print 2>/dev/null || true
echo "--- Finding Core OS files ---"
xorriso -indev "$ISO_PATH" -find / -name "vmlinuz*" -print 2>/dev/null || true
xorriso -indev "$ISO_PATH" -find / -name "initrd*" -print 2>/dev/null || true
xorriso -indev "$ISO_PATH" -find / -name "filesystem.squashfs" -print 2>/dev/null || true
