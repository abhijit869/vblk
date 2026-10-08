#!/bin/bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR/../../"
sudo ./scripts/build/preflight.sh
sudo ./scripts/build/clean.sh

# Ensure model and llama.cpp exist
./scripts/build/fetch-local-model.sh
./scripts/build/build-llama-cpp.sh

sudo mkdir -p /tmp/jarvis_build
sudo cp -r iso python systemd desktop config scripts downloads dist /tmp/jarvis_build/
sudo chown -R $USER:$USER /tmp/jarvis_build
cd /tmp/jarvis_build/iso
sudo ./build.sh
echo "=> Starting live-build process..."
sudo lb build > build.log 2>&1
if [ -f "live-image-amd64.hybrid.iso" ]; then
    echo "=> Build successful!"
    mkdir -p /workspaces/vblk/dist
    cp live-image-amd64.hybrid.iso /workspaces/vblk/dist/JARVIS-OS-1.0-amd64.iso
    cd /workspaces/vblk/dist
    sha256sum JARVIS-OS-1.0-amd64.iso > JARVIS-OS-1.0-amd64.iso.sha256
    sha512sum JARVIS-OS-1.0-amd64.iso > JARVIS-OS-1.0-amd64.iso.sha512
    echo "=> ISO copied to dist/ and checksums generated."
else
    echo "=> Build failed! Check /tmp/jarvis_build/iso/build.log"
    exit 1
fi

cd /workspaces/vblk
./scripts/build/generate-manifest.sh
