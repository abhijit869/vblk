#!/usr/bin/env python3
"""Desktop Wallpaper Daemon for JARVIS OS.

Listens to D-Bus signals from com.jarvis.WallpaperInterface and updates
the desktop background using feh. Also sets the background on startup.
"""

import sys
import json
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib
except ImportError:
    logger.error("dbus-python or PyGObject is not installed. Wallpaper daemon cannot start.")
    sys.exit(1)

def apply_wallpaper(path: str):
    logger.info(f"Applying wallpaper: {path}")
    try:
        import os
        os.spawnvp(os.P_WAIT, "feh", ["feh", "--bg-scale", path])
    except Exception as e:
        logger.error(f"Failed to run feh: {e}")

def on_wallpaper_changed(path: str):
    apply_wallpaper(path)

def main():
    DBusGMainLoop(set_as_default=True)
    try:
        bus = dbus.SystemBus()
    except dbus.DBusException as e:
        logger.error(f"Failed to connect to system bus: {e}")
        return

    try:
        proxy = bus.get_object("com.jarvis.Core", "/com/jarvis/Wallpaper")
        iface = dbus.Interface(proxy, "com.jarvis.WallpaperInterface")
        
        # Get initial wallpaper
        current_json = iface.GetCurrent()
        current = json.loads(current_json)
        if "path" in current:
            apply_wallpaper(current["path"])
            
        # Listen for changes
        iface.connect_to_signal("WallpaperChanged", on_wallpaper_changed)
        
        logger.info("Wallpaper daemon running and listening for changes...")
        loop = GLib.MainLoop()
        loop.run()
    except dbus.DBusException as e:
        logger.error(f"Could not connect to WallpaperInterface: {e}. Is jarvis-core running?")

if __name__ == "__main__":
    main()
