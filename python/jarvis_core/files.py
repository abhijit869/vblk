import os
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List

from jarvis_core.pathguard import PathGuard

class FileService:
    @staticmethod
    def _format_stat(st) -> Dict[str, Any]:
        return {
            "size": st.st_size,
            "modified": st.st_mtime,
            "is_dir": os.path.isdir(st) if hasattr(st, "st_mode") else False # wait, S_ISDIR is better, but this is simple.
        }

    @staticmethod
    def list_dir(path: str | Path) -> Dict[str, Any]:
        ok, reason = PathGuard.check_read(path)
        if not ok:
            return {"success": False, "error": reason}
        
        try:
            p = Path(path).expanduser().resolve()
            entries = []
            for entry in os.scandir(p):
                st = entry.stat(follow_symlinks=False)
                entries.append({
                    "name": entry.name,
                    "is_dir": entry.is_dir(follow_symlinks=False),
                    "is_symlink": entry.is_symlink(),
                    "size": st.st_size,
                    "modified": st.st_mtime
                })
            return {"success": True, "entries": entries, "path": str(p)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def stat(path: str | Path) -> Dict[str, Any]:
        ok, reason = PathGuard.check_read(path)
        if not ok:
            return {"success": False, "error": reason}
            
        try:
            p = Path(path).expanduser().resolve()
            st = p.stat(follow_symlinks=False)
            return {
                "success": True,
                "name": p.name,
                "is_dir": p.is_dir(),
                "is_symlink": p.is_symlink(),
                "size": st.st_size,
                "modified": st.st_mtime,
                "path": str(p)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def mkdir(path: str | Path) -> Dict[str, Any]:
        ok, reason = PathGuard.check_write(path)
        if not ok:
            return {"success": False, "error": reason}
        try:
            p = Path(path).expanduser()
            p.mkdir(parents=False, exist_ok=False)
            return {"success": True, "path": str(p)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def copy(src: str | Path, dst: str | Path) -> Dict[str, Any]:
        ok_s, reason_s = PathGuard.check_read(src)
        if not ok_s: return {"success": False, "error": f"Source: {reason_s}"}
        ok_d, reason_d = PathGuard.check_write(dst)
        if not ok_d: return {"success": False, "error": f"Destination: {reason_d}"}
        
        try:
            s = Path(src).expanduser()
            d = Path(dst).expanduser()
            if s.resolve() in d.resolve().parents or s.resolve() == d.resolve():
                return {"success": False, "error": "Destination is inside source"}
            if s.is_dir():
                shutil.copytree(s, d, symlinks=True)
            else:
                shutil.copy2(s, d, follow_symlinks=False)
            return {"success": True, "path": str(d)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def move(src: str | Path, dst: str | Path) -> Dict[str, Any]:
        ok_s, reason_s = PathGuard.check_write(src)
        if not ok_s: return {"success": False, "error": f"Source: {reason_s}"}
        ok_d, reason_d = PathGuard.check_write(dst)
        if not ok_d: return {"success": False, "error": f"Destination: {reason_d}"}
        
        try:
            s = Path(src).expanduser()
            d = Path(dst).expanduser()
            if s.resolve() in d.resolve().parents or s.resolve() == d.resolve():
                return {"success": False, "error": "Destination is inside source"}
            shutil.move(str(s), str(d))
            return {"success": True, "path": str(d)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def rename(src: str | Path, name: str) -> Dict[str, Any]:
        ok_s, reason_s = PathGuard.check_write(src)
        if not ok_s: return {"success": False, "error": f"Source: {reason_s}"}
        
        try:
            s = Path(src).expanduser()
            if not name or name in {".", ".."} or "/" in name or "\0" in name:
                return {"success": False, "error": "Invalid name"}
            if len(name.encode('utf-8')) > 255:
                return {"success": False, "error": "Name too long"}
                
            d = s.with_name(name)
            ok_d, reason_d = PathGuard.check_write(d)
            if not ok_d: return {"success": False, "error": f"Destination: {reason_d}"}
            
            s.rename(d)
            return {"success": True, "path": str(d)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def trash(path: str | Path) -> Dict[str, Any]:
        ok, reason = PathGuard.check_write(path)
        if not ok: return {"success": False, "error": reason}
        
        try:
            p = Path(path).expanduser()
            import urllib.parse
            import uuid
            
            # Use gio trash if available (usually available on modern Linux)
            gio = shutil.which("gio")
            if gio:
                import subprocess
                res = subprocess.run([gio, "trash", str(p)], capture_output=True, text=True)
                if res.returncode == 0:
                    return {"success": True, "path": str(p)}
            
            # Fallback to XDG trash spec
            home = Path.home()
            trash_root = Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share")) / "Trash"
            files_dir = trash_root / "files"
            info_dir = trash_root / "info"
            
            files_dir.mkdir(parents=True, exist_ok=True)
            info_dir.mkdir(parents=True, exist_ok=True)
            
            # Find unique name
            stem = p.stem
            suffix = p.suffix
            destination = files_dir / p.name
            if destination.exists() or destination.is_symlink():
                for idx in range(1, 10000):
                    candidate = files_dir / f"{stem} ({idx}){suffix}"
                    if not candidate.exists() and not candidate.is_symlink():
                        destination = candidate
                        break
                else:
                    destination = files_dir / f"{stem}-{uuid.uuid4().hex[:8]}{suffix}"
            
            shutil.move(str(p), str(destination))
            
            info_name = destination.name + ".trashinfo"
            # Must percent encode the path per spec
            # Remove trailing slash if dir for URI but keep as path
            enc_path = urllib.parse.quote(str(p.resolve()))
            deletion_date = time.strftime("%Y-%m-%dT%H:%M:%S")
            
            (info_dir / info_name).write_text(
                "[Trash Info]\n"
                f"Path={enc_path}\n"
                f"DeletionDate={deletion_date}\n",
                encoding="utf-8"
            )
            return {"success": True, "path": str(p)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def search(root: str | Path, query: str) -> Dict[str, Any]:
        ok, reason = PathGuard.check_read(root)
        if not ok: return {"success": False, "error": reason}
        
        try:
            r = Path(root).expanduser().resolve()
            needle = query.casefold()
            matches = []
            # simple walk, no symlink follow
            for base, dirs, files in os.walk(r, topdown=True, followlinks=False):
                # We can't yield an unbounded list; cap at 2000
                for name in [*dirs, *files]:
                    if needle in name.casefold():
                        matches.append(str(Path(base) / name))
                        if len(matches) >= 2000:
                            return {"success": True, "entries": matches, "truncated": True}
            return {"success": True, "entries": matches, "truncated": False}
        except Exception as e:
            return {"success": False, "error": str(e)}
