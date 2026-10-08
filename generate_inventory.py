import json

packages = []
with open("iso/config/package-lists/jarvis.list.chroot") as f:
    packages = [line.strip() for line in f if line.strip() and not line.startswith("#")]

inventory = []

categories = {
    "Core": ["jarvis-shell", "jarvis-core", "dbus", "systemd", "xorg", "openbox"],
    "Standard": ["firefox-esr", "libreoffice", "vlc", "evince", "eog", "file-roller", "mousepad", "gnome-calculator"],
    "Developer": ["git", "git-lfs", "python3", "gcc", "g++", "make", "cmake", "ninja-build", "pkg-config", "neovim"],
    "Network": ["network-manager", "wpa_supplicant", "iw", "iproute2"],
    "Firmware": ["firmware-linux", "firmware-amd-graphics", "intel-microcode", "amd64-microcode"]
}

for pkg in packages:
    cat = "System"
    for c, pkgs in categories.items():
        if pkg in pkgs:
            cat = c
            break
            
    inventory.append({
        "name": pkg,
        "Debian package": pkg,
        "version": "latest",
        "category": cat,
        "source": "Debian",
        "installed-by-default": True,
        "desktop-file": "N/A",
        "executable": pkg,
        "package-size": "unknown"
    })

with open("reports/preinstalled-apps.json", "w") as f:
    json.dump(inventory, f, indent=4)
