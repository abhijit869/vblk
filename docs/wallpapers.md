# JARVIS OS Wallpaper System

## Overview
The JARVIS OS wallpaper system is designed to provide a robust, production-quality visual identity management for the OS, with the 3rd reference image established as the canonical JARVIS Default Wallpaper.

## Architecture
- **Backend**: `WallpaperManager` in `python/jarvis_core/wallpaper.py` handles state, metadata, and safe file copies. Wallpapers are stored in `/var/lib/jarvis/wallpapers.json` and user wallpapers in `/var/lib/jarvis/user_wallpapers`.
- **D-Bus Interface**: `com.jarvis.WallpaperInterface` allows frontend components to query and set wallpapers securely, emitting `WallpaperChanged` signals.
- **Frontend App**: `desktop/jarvis_panel.py` features an Appearance tab where users can preview, add, delete, and apply wallpapers.
- **File Explorer**: Integrated context menu options to "Set as Wallpaper" and "Add to Wallpaper Library".
- **Daemon**: `desktop/wallpaper_daemon.py` acts as a tier-1 desktop client, autostarted by openbox, applying wallpapers via `feh` and listening to D-Bus changes.
- **AI Tools**: AI can manage wallpapers via `wallpaper.*` tools.

## Visual Identity
The system enforces a strict fallback mechanism to the default `jarvis-default` asset to ensure the visual identity of JARVIS OS is never lost or corrupted.
