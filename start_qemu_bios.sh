#!/bin/bash
qemu-system-x86_64 \
    -m 2048 -smp 2 \
    -drive file=dist/JARVIS-OS-1.0-amd64.iso,format=raw,media=cdrom \
    -boot d \
    -net nic -net user,hostfwd=tcp::2225-:22 \
    -vnc :1 \
    -qmp unix:/tmp/qmp-bios.sock,server,nowait \
    -daemonize
