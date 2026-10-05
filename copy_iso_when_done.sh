#!/bin/bash
# Wait for lb build to start if it hasn't yet
sleep 5
while kill -0 $(pgrep -f "lb build" | head -n 1) 2>/dev/null; do
    sleep 5
done
if [ -f /tmp/jarvis_build/iso/live-image-amd64.hybrid.iso ]; then
    cp /tmp/jarvis_build/iso/live-image-amd64.hybrid.iso /workspaces/vblk/iso/
    echo "ISO successfully copied to workspace!" > /workspaces/vblk/iso/build_success.txt
fi
