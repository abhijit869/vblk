#!/usr/bin/env bash
# JARVIS OS ISO Builder - High Performance VM Edition

set -e

echo "=> Initializing Debian Live Build for JARVIS OS (4GB VM Optimized)..."
lb config \
    --mode debian \
    --distribution bookworm \
    --architecture amd64 \
    --archive-areas "main contrib non-free-firmware" \
    --iso-application "JARVIS OS" \
    --iso-publisher "JARVIS AI Systems" \
    --iso-volume "JARVIS_OS_1.0" \
    --memtest none \
    --parent-mirror-bootstrap "http://deb.debian.org/debian/" \
    --parent-mirror-chroot "http://deb.debian.org/debian/" \
    --parent-mirror-binary "http://deb.debian.org/debian/" \
    --mirror-bootstrap "http://deb.debian.org/debian/" \
    --mirror-chroot "http://deb.debian.org/debian/" \
    --mirror-binary "http://deb.debian.org/debian/" \
    --binary-images iso-hybrid \
    --keyring-packages debian-archive-keyring \
    --linux-packages "linux-image" \
    --initramfs live-boot \
    --bootappend-live "boot=live components quiet splash mitigations=off" # Disable mitigations for max VM performance

echo "=> Deep integrating JARVIS into Debian chroot..."
mkdir -p config/includes.chroot/opt/jarvis/
cp -r ../python ../systemd ../desktop config/includes.chroot/opt/jarvis/

# Systemd services
cp ../systemd/jarvis-core.service config/includes.chroot/etc/systemd/system/
cp ../systemd/jarvis-eventbus.service config/includes.chroot/etc/systemd/system/

# Post-install hooks
cat << 'HOOK' > config/hooks/normal/01-enable-jarvis.hook.chroot
#!/bin/sh
# 1. Enable services
systemctl enable jarvis-core.service
systemctl enable jarvis-eventbus.service
systemctl enable zramswap.service

# 2. Setup Jarvis user and GUI autologin
useradd -m -s /bin/bash jarvis
chown -R jarvis:jarvis /opt/jarvis

# 3. Precompile Python to bytecode for faster startup and lower RAM usage
python3 -m compileall /opt/jarvis/python/jarvis_core

# 4. Limit malloc arenas for JARVIS daemon to reduce memory fragmentation footprint
sed -i 's/Environment="JARVIS_AI_PROVIDER/Environment="MALLOC_ARENA_MAX=2"\nEnvironment="JARVIS_AI_PROVIDER/g' /etc/systemd/system/jarvis-core.service
HOOK
chmod +x config/hooks/normal/01-enable-jarvis.hook.chroot

echo "=> Build setup complete! Run 'sudo lb build' to generate the highly optimized ISO."
