#!/usr/bin/env bash
# JARVIS OS ISO Builder - High Performance VM Edition

set -e

echo "=> Initializing Debian Live Build for JARVIS OS (4GB VM Optimized)..."
export MKSQUASHFS_OPTIONS="-mem 2G"
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
    --security false \
    --binary-images iso-hybrid \
    --keyring-packages debian-archive-keyring \
    --linux-packages "linux-image" \
    --linux-flavours "amd64" \
    --firmware-binary false \
    --firmware-chroot false \
    --bootloaders "syslinux grub-efi" \
    --uefi-secure-boot auto \
    --initramfs live-boot \
    --bootappend-live "boot=live components quiet splash mitigations=off" # Disable mitigations for max VM performance

echo "=> Deep integrating JARVIS into Debian chroot..."
mkdir -p config/includes.chroot/opt/jarvis/
cp -r ../python ../systemd ../desktop config/includes.chroot/opt/jarvis/

# Systemd services
cp ../systemd/jarvis-core.service config/includes.chroot/etc/systemd/system/
cp ../systemd/jarvis-eventbus.service config/includes.chroot/etc/systemd/system/
cp ../systemd/jarvis-local-ai.service config/includes.chroot/etc/systemd/system/ 

mkdir -p config/includes.chroot/usr/lib/jarvis/models/emergency 
mkdir -p config/includes.chroot/usr/lib/jarvis/llama.cpp 
mkdir -p config/includes.chroot/usr/lib/jarvis/scripts 
mkdir -p config/includes.chroot/etc/jarvis 
mkdir -p config/includes.chroot/etc/sudoers.d 
mkdir -p config/includes.chroot/etc/dbus-1/system.d
cp ../config/dbus/com.jarvis.Core.conf config/includes.chroot/etc/dbus-1/system.d/
mkdir -p config/includes.chroot/usr/local/bin
mkdir -p config/includes.chroot/usr/local/lib
cp ../downloads/models/Qwen3-1.7B-Q4_K_M.gguf config/includes.chroot/usr/lib/jarvis/models/emergency/ || true 
cp ../dist/llama.cpp/llama-server config/includes.chroot/usr/local/bin/ || true 
cp -a ../dist/llama.cpp/lib*.so* config/includes.chroot/usr/local/lib/ || true 
cp ../config/local-ai/jarvis-local-ai.env config/includes.chroot/etc/jarvis/local-ai.env || true 
cp ../scripts/local-ai-lifecycle.sh config/includes.chroot/usr/lib/jarvis/scripts/ || true 
chmod +x config/includes.chroot/usr/lib/jarvis/scripts/local-ai-lifecycle.sh || true 
cp ../config/local-ai/sudoers.d/jarvis-local-ai config/includes.chroot/etc/sudoers.d/ || true 
chmod 440 config/includes.chroot/etc/sudoers.d/jarvis-local-ai || true 


# Post-install hooks
cat << 'HOOK' > config/hooks/normal/01-enable-jarvis.hook.chroot
#!/bin/sh
ldconfig
# 1. Enable services
systemctl enable jarvis-core.service
systemctl enable jarvis-eventbus.service
systemctl enable zramswap.service

# 2. Setup Jarvis user and GUI autologin
if ! id -u jarvis >/dev/null 2>&1; then
    useradd -m -s /bin/bash jarvis
    echo "jarvis:jarvis" | chpasswd
    usermod -aG sudo jarvis
fi
chown -R jarvis:jarvis /opt/jarvis
# Create log and lib directories for jarvis
mkdir -p /var/log/jarvis/local-ai /var/lib/jarvis/local-ai
chown -R jarvis:jarvis /var/log/jarvis /var/lib/jarvis

# 3. Precompile Python to bytecode for faster startup and lower RAM usage
python3 -m compileall /opt/jarvis/python/jarvis_core

# 4. Limit malloc arenas for JARVIS daemon to reduce memory fragmentation footprint
sed -i 's/Environment="JARVIS_AI_PROVIDER/Environment="MALLOC_ARENA_MAX=2"\nEnvironment="JARVIS_AI_PROVIDER/g' /etc/systemd/system/jarvis-core.service

# 5. Install Desktop Application Icon
mkdir -p /usr/share/applications
cp /opt/jarvis/desktop/jarvis-panel.desktop /usr/share/applications/
chmod 644 /usr/share/applications/jarvis-panel.desktop
mkdir -p /usr/share/pixmaps
cp /opt/jarvis/desktop/jarvis-files.desktop /usr/share/applications/
chmod 644 /usr/share/applications/jarvis-files.desktop
cp /opt/jarvis/desktop/icons/jarvis-files.svg /usr/share/pixmaps/
chmod 644 /usr/share/pixmaps/jarvis-files.svg
su - jarvis -c "xdg-mime default jarvis-files.desktop inode/directory"
xdg-mime default jarvis-files.desktop inode/directory
HOOK
chmod +x config/hooks/normal/01-enable-jarvis.hook.chroot

echo "=> Build setup complete! Run 'sudo lb build' to generate the highly optimized ISO."

mkdir -p config/includes.chroot/etc/ssh/sshd_config.d
echo "PasswordAuthentication yes" > config/includes.chroot/etc/ssh/sshd_config.d/live.conf
