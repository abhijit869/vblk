import os
import json
import uuid
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

WALLPAPER_DB_PATH = "/var/lib/jarvis/wallpapers.json"
USER_WALLPAPER_DIR = "/var/lib/jarvis/user_wallpapers"
BUILTIN_WALLPAPER_DIR = "/opt/jarvis/desktop/themes/wallpapers/jarvis"

# Default fallback
DEFAULT_ID = "jarvis-default"

class WallpaperManager:
    def __init__(self):
        self.db_path = Path(WALLPAPER_DB_PATH)
        self.user_dir = Path(USER_WALLPAPER_DIR)
        
        # User wallpaper directory requires user access, handled in daemon setup
        self._cache = self._load_db()
        self._ensure_builtins()

    def _load_db(self) -> Dict[str, Any]:
        if self.db_path.exists():
            try:
                return json.loads(self.db_path.read_text())
            except Exception as e:
                logger.error(f"Failed to load wallpaper DB: {e}")
        
        return {
            "current": DEFAULT_ID,
            "wallpapers": {}
        }

    def _save_db(self):
        try:
            # Atomic save to prevent corruption
            tmp_path = self.db_path.with_suffix('.tmp')
            tmp_path.write_text(json.dumps(self._cache, indent=2))
            tmp_path.replace(self.db_path)
            # Ensure proper permissions
            os.chmod(self.db_path, 0o644)
        except Exception as e:
            logger.error(f"Failed to save wallpaper DB: {e}")

    def _ensure_builtins(self):
        builtins = {
            "jarvis-default": {
                "name": "JARVIS Default",
                "filename": "jarvis-default.jpeg",
                "default": True,
                "favorite": True
            },
            "jarvis-alt-1": {
                "name": "JARVIS Alternate 1",
                "filename": "jarvis-alt-1.jpeg",
                "default": False,
                "favorite": False
            },
            "jarvis-alt-2": {
                "name": "JARVIS Alternate 2",
                "filename": "jarvis-alt-2.jpeg",
                "default": False,
                "favorite": False
            }
        }
        
        changed = False
        for wid, meta in builtins.items():
            if wid not in self._cache["wallpapers"]:
                self._cache["wallpapers"][wid] = {
                    "id": wid,
                    "name": meta["name"],
                    "source": "built-in",
                    "path": str(Path(BUILTIN_WALLPAPER_DIR) / meta["filename"]),
                    "category": "JARVIS",
                    "built_in": True,
                    "default": meta["default"],
                    "favorite": meta["favorite"],
                    "deletable": False
                }
                changed = True
                
        to_remove = []
        for wid, meta in self._cache["wallpapers"].items():
            if meta.get("source") == "user":
                if not Path(meta["path"]).exists():
                    to_remove.append(wid)
        for wid in to_remove:
            del self._cache["wallpapers"][wid]
            changed = True
            
        if self._cache.get("current") not in self._cache["wallpapers"]:
            self._cache["current"] = DEFAULT_ID
            changed = True

        if changed:
            self._save_db()

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self._cache["wallpapers"].values())

    def get_current(self) -> Dict[str, Any]:
        current_id = self._cache.get("current", DEFAULT_ID)
        if current_id not in self._cache["wallpapers"] or not Path(self._cache["wallpapers"][current_id]["path"]).exists():
            self._cache["current"] = DEFAULT_ID
            self._save_db()
            current_id = DEFAULT_ID
        return self._cache["wallpapers"][current_id]

    def set_current(self, wallpaper_id: str) -> bool:
        if wallpaper_id in self._cache["wallpapers"]:
            meta = self._cache["wallpapers"][wallpaper_id]
            if Path(meta["path"]).exists():
                self._cache["current"] = wallpaper_id
                self._save_db()
                return True
        return False

    def reset_default(self) -> bool:
        return self.set_current(DEFAULT_ID)

    def set_favorite(self, wallpaper_id: str, favorite: bool) -> bool:
        if wallpaper_id in self._cache["wallpapers"]:
            self._cache["wallpapers"][wallpaper_id]["favorite"] = favorite
            self._save_db()
            return True
        return False

    def _validate_image(self, path: Path) -> bool:
        if not path.is_file():
            return False
        
        if path.stat().st_size > 20 * 1024 * 1024:
            return False
            
        try:
            with open(path, "rb") as f:
                header = f.read(16)
        except Exception:
            return False
            
        if header.startswith(b"\xff\xd8\xff"):
            return True
        if header.startswith(b"\x89PNG\x0d\x0a\x1a\x0a"):
            return True
        if header[0:4] == b"RIFF" and header[8:12] == b"WEBP":
            return True
            
        return False

    def add_user_wallpaper(self, source_path: str, name: str) -> Optional[Dict[str, Any]]:
        src = Path(source_path).resolve()
        
        if not self._validate_image(src):
            raise ValueError("Invalid image file. Only JPEG, PNG, and WEBP under 20MB are supported.")
            
        wid = f"wallpaper-{uuid.uuid4().hex[:12]}"
        ext = src.suffix.lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            ext = ".jpg"
            
        self.user_dir.mkdir(parents=True, exist_ok=True)
        dest = self.user_dir / f"{wid}{ext}"
        
        try:
            shutil.copy2(src, dest)
            os.chmod(dest, 0o644)
        except Exception as e:
            logger.error(f"Failed to copy wallpaper: {e}")
            raise RuntimeError(f"Failed to import wallpaper: {e}")

        meta = {
            "id": wid,
            "name": name or src.name,
            "source": "user",
            "path": str(dest),
            "category": "User",
            "built_in": False,
            "default": False,
            "favorite": False,
            "deletable": True
        }
        
        self._cache["wallpapers"][wid] = meta
        self._save_db()
        return meta

    def remove_user_wallpaper(self, wallpaper_id: str) -> bool:
        if wallpaper_id not in self._cache["wallpapers"]:
            return False
            
        meta = self._cache["wallpapers"][wallpaper_id]
        if meta.get("built_in") or not meta.get("deletable"):
            raise ValueError("Cannot delete built-in wallpaper")
            
        path = Path(meta["path"])
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass
                
        del self._cache["wallpapers"][wallpaper_id]
        
        if self._cache.get("current") == wallpaper_id:
            self._cache["current"] = DEFAULT_ID
            
        self._save_db()
        return True
