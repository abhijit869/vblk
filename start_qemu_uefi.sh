#!/bin/bash
qemu-system-x86_64 \
    -m 2048 -smp 2 \
    -bios /usr/share/ovmf/OVMF.fd \
    -drive file=dist/JARVIS-OS-1.0-amd64.iso,format=raw,media=cdrom \
    -boot d \
    -net nic -net user,hostfwd=tcp::2226-:22 \
    -vnc :2 \
    -qmp unix:/tmp/qmp-uefi.sock,server,nowait \
    -daemonize
