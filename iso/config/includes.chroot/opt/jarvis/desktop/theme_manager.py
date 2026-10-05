#!/usr/bin/env python3
"""Desktop Theme Manager for JARVIS OS.

Merges concepts from Windows 11 (centered taskbar, rounded corners, snap layouts)
and macOS (global menu bar, blur effects, dock).
"""

import json
import urllib.request
from pathlib import Path

# A curated list of elegant wallpapers representing the OS theme
WALLPAPERS = {
    "light": "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?w=1920&q=80", # Gradient light
    "dark": "https://images.unsplash.com/photo-1550684848-fac1c5b4e853?w=1920&q=80",   # Abstract dark
}

GTK_THEME_TEMPLATE = """
/* JARVIS OS Hybrid Theme - Merging Win11 & macOS */
window {
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.25);
}

headerbar {
    /* macOS style unified titlebar/toolbar */
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(20px);
}

#Taskbar {
    /* Windows 11 style centered dock/taskbar */
    border-radius: 16px;
    margin-bottom: 8px;
    background: rgba(255, 255, 255, 0.9);
}
"""

def setup_themes(base_dir: str = "desktop/themes"):
    path = Path(base_dir)
    path.mkdir(parents=True, exist_ok=True)
    
    # 1. Download Wallpapers
    wallpaper_dir = path / "wallpapers"
    wallpaper_dir.mkdir(exist_ok=True)
    
    print("Fetching background images...")
    for name, url in WALLPAPERS.items():
        dest = wallpaper_dir / f"{name}_wallpaper.jpg"
        if not dest.exists():
            try:
                # Add headers to avoid 403 on some CDNs
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response, open(dest, 'wb') as out_file:
                    out_file.write(response.read())
                print(f"Downloaded: {dest}")
            except Exception as e:
                print(f"Failed to download {name}: {e}")
                
    # 2. Generate CSS Theme Template
    theme_file = path / "jarvis-hybrid.css"
    theme_file.write_text(GTK_THEME_TEMPLATE)
    print(f"Generated GUI Theme template: {theme_file}")

    # 3. Create Desktop Environment Configuration
    config = {
        "desktop_environment": "JARVIS AI Shell",
        "dock_position": "bottom-center",  # Win 11 style
        "global_menu": True,               # Mac OS style
        "window_controls": "left",         # Mac OS style
        "corner_radius": 12,
        "blur_effects": True,
        "ai_integration": {
            "file_explorer": True,
            "navigation": True,
            "assistant_shortcut": "Super+Space"
        }
    }
    config_file = path / "desktop_config.json"
    config_file.write_text(json.dumps(config, indent=2))
    print(f"Generated Desktop Config: {config_file}")


if __name__ == "__main__":
    setup_themes()
