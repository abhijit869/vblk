#!/usr/bin/env bash
# JARVIS OS ISO Builder
# Requires: live-build, debootstrap, squashfs-tools, xorriso

set -e

echo "=> Initializing Debian Live Build for JARVIS OS..."
lb config \
    --distribution bookworm \
    --architecture amd64 \
    --archive-areas "main contrib non-free-firmware" \
    --iso-application "JARVIS OS" \
    --iso-publisher "JARVIS AI Systems" \
    --iso-volume "JARVIS_OS_1.0" \
    --memtest none \
    --binary-images iso-hybrid

echo "=> Configuring packages..."
# Install base utilities, D-Bus, systemd, bwrap (for sandboxing), and python
cat << 'PKG' > config/package-lists/jarvis.list.chroot
linux-image-amd64
systemd
systemd-sysv
dbus
bubblewrap
python3
python3-pip
python3-venv
xorg
openbox
wmctrl
xdotool
scrot
iptables
PKG

echo "=> Copying JARVIS Core into ISO chroot..."
# Assuming we run this from the project root
cp -r ../python ../systemd ../desktop config/includes.chroot/opt/jarvis/

# Set up systemd services
cp ../systemd/jarvis-core.service config/includes.chroot/etc/systemd/system/
cp ../systemd/jarvis-eventbus.service config/includes.chroot/etc/systemd/system/

echo "=> Writing chroot hook to enable services..."
mkdir -p config/hooks/normal
cat << 'HOOK' > config/hooks/normal/01-enable-jarvis.hook.chroot
#!/bin/sh
systemctl enable jarvis-core.service
systemctl enable jarvis-eventbus.service

# Create jarvis user
useradd -m -s /bin/bash jarvis
chown -R jarvis:jarvis /opt/jarvis
HOOK
chmod +x config/hooks/normal/01-enable-jarvis.hook.chroot

echo "=> Configuration complete. To build, run 'lb build' as root."
