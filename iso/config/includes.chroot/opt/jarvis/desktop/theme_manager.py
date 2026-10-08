#!/usr/bin/env python3
"""Desktop Theme Manager for JARVIS OS.

Merges concepts from Windows 11 (centered taskbar, rounded corners, snap layouts)
and macOS (global menu bar, blur effects, dock).
"""

import json
from pathlib import Path

WALLPAPERS = {
    "dark": "dark_wallpaper.jpg",
    "light": "light_wallpaper.jpg",
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
    
    # 1. Register bundled wallpapers
    wallpaper_dir = path / "wallpapers"
    wallpaper_dir.mkdir(exist_ok=True)
    missing_wallpapers = [filename for filename in WALLPAPERS.values()
                          if not (wallpaper_dir / filename).is_file()]
    if missing_wallpapers:
        raise FileNotFoundError(
            f"Missing bundled wallpapers: {', '.join(missing_wallpapers)}"
        )
                
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
        "gtk_theme": "MacTahoe-Dark",
        "icon_theme": "MacTahoe",
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
