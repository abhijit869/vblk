#!/bin/bash
sudo rm -rf /tmp/jarvis_build
mkdir -p /tmp/jarvis_build
cp -r /workspaces/vblk/iso /tmp/jarvis_build/
cp -r /workspaces/vblk/python /tmp/jarvis_build/
cp -r /workspaces/vblk/systemd /tmp/jarvis_build/
cp -r /workspaces/vblk/desktop /tmp/jarvis_build/
cd /tmp/jarvis_build/iso
sudo ./build.sh
sudo lb build > build.log 2>&1
