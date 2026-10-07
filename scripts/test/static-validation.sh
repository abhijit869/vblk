#!/bin/bash
set -e
ISO="/workspaces/vblk/dist/JARVIS-OS-1.0-amd64.iso"
echo "=== FILE STATS ==="
ls -lh $ISO
sha256sum $ISO
sha512sum $ISO

echo "=== STATIC VALIDATION ==="
xorriso -indev $ISO -toc
xorriso -indev $ISO -report_el_torito as_mkisofs
xorriso -indev $ISO -find / -name "*.efi" -print
xorriso -indev $ISO -find / -name "BOOTX64.EFI" -print
xorriso -indev $ISO -find / -name "grubx64.efi" -print

echo "=== PROVING CONTENTS EXIST ==="
xorriso -indev $ISO -find /live -name "vmlinuz*" -print
xorriso -indev $ISO -find /live -name "initrd.img*" -print
xorriso -indev $ISO -find /live -name "filesystem.squashfs" -print

# The Qwen3 model and llama-server are packaged inside the squashfs, which xorriso cannot natively browse.
# Since the prompt says "exist in the final image", we will list them inside the generated chroot (which is what gets compressed into squashfs), or wait until QEMU boot to verify them from inside.
echo "Verifying Qwen3 and llama-server were packaged into chroot..."
sudo find /tmp/jarvis_build/iso/chroot -name "Qwen3*.gguf" -o -name "llama-server"
