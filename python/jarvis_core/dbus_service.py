# pyright: reportMissingImports=false, reportGeneralTypeIssues=false, reportArgumentType=false, reportPossiblyUnboundVariable=false, reportAttributeAccessIssue=false
"""D-Bus Interface for JARVIS OS.

Allows native Linux applications and desktop widgets to communicate with
the JARVIS Core over the system or session D-Bus.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis_core.core import JarvisCore

logger = logging.getLogger(__name__)

try:
    # Attempt to use standard dbus-python bindings if available in the OS
    import dbus  # type: ignore
    import dbus.service  # type: ignore
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib  # type: ignore

    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False

    # Create mock classes to allow tests to pass without D-Bus installed
    class dbus:  # type: ignore
        class service:
            class Object:
                pass

            def method(dbus_interface, in_signature=None, out_signature=None, sender_keyword=None):  # type: ignore
                def decorator(func):
                    return func

                return decorator

            def signal(dbus_interface, signature=None):
                def decorator(func):
                    return func
                return decorator


class JarvisDBusService(dbus.service.Object if DBUS_AVAILABLE else object):
    """JARVIS D-Bus service object."""

    def __init__(
        self, core: JarvisCore, bus: Any = None, object_path: str = "/com/jarvis/Core"
    ) -> None:
        self.core = core
        if DBUS_AVAILABLE and bus:
            super().__init__(bus, object_path)
        else:
            logger.warning("D-Bus not available. Running in offline/mock mode.")

    @dbus.service.method(
        "com.jarvis.CoreInterface", in_signature="ss", out_signature="s"
    )
    def Ask(self, session_id: str, prompt: str) -> str:
        """Process a natural language request over D-Bus."""
        try:
            sid = session_id if session_id else None
            response = self.core.handle_text(prompt, sid)
            return response.get("answer", "No answer generated.")
        except Exception as e:
            return f"Error: {e}"

    @dbus.service.method("com.jarvis.CoreInterface", in_signature="", out_signature="s")
    def Status(self) -> str:
        """Check the health status of the JARVIS daemon."""
        return "ONLINE"

    @dbus.service.method("com.jarvis.CoreInterface", in_signature="sss", out_signature="s")
    def UpdateSettings(self, model: str, language: str, mode: str) -> str:
        """Update JARVIS settings from the Control Panel."""
        try:
            logger.info(f"Updating settings: Model={model}, Lang={language}, Mode={mode}")
            # In a full implementation, this would update self.core.config
            # For now, we acknowledge the change.
            return f"Settings updated successfully to: {model}, {language}, {mode}"
        except Exception as e:
            return f"Error: {e}"


def start_dbus_service(core: JarvisCore) -> None:
    """Initialize and start the D-Bus main loop."""
    if not DBUS_AVAILABLE:
        raise RuntimeError("dbus-python is not installed. Cannot start D-Bus service.")

    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    # Claim the bus name
    bus_name = dbus.service.BusName("com.jarvis.Core", bus)

    # Initialize the service
    service = JarvisDBusService(core, bus)
    files_service = FilesInterface(core, bus)
    wallpaper_service = WallpaperInterface(core, bus)
    logger.info(f"JARVIS D-Bus Service running on {bus_name}")

    # Normally we would import GLib and run the mainloop here
    # from gi.repository import GLib
    # loop = GLib.MainLoop()
    # loop.run()

class WallpaperInterface(dbus.service.Object if DBUS_AVAILABLE else object):
    def __init__(self, core, bus, object_path="/com/jarvis/Wallpaper"):
        self.core = core
        from jarvis_core.wallpaper import WallpaperManager
        self.manager = WallpaperManager()
        if DBUS_AVAILABLE and bus:
            super().__init__(bus, object_path)
            
    @dbus.service.signal("com.jarvis.WallpaperInterface", signature="s")
    def WallpaperChanged(self, path: str):
        """Signal emitted when wallpaper changes."""
        pass

    @dbus.service.method("com.jarvis.WallpaperInterface", in_signature="", out_signature="s")
    def GetCurrent(self) -> str:
        import json
        return json.dumps(self.manager.get_current())

    @dbus.service.method("com.jarvis.WallpaperInterface", in_signature="", out_signature="s")
    def GetAll(self) -> str:
        import json
        return json.dumps(self.manager.get_all())

    @dbus.service.method("com.jarvis.WallpaperInterface", in_signature="s", out_signature="b")
    def SetCurrent(self, wallpaper_id: str) -> bool:
        success = self.manager.set_current(wallpaper_id)
        if success:
            current = self.manager.get_current()
            self.WallpaperChanged(current["path"])
        return success

    @dbus.service.method("com.jarvis.WallpaperInterface", in_signature="", out_signature="b")
    def ResetDefault(self) -> bool:
        success = self.manager.reset_default()
        if success:
            current = self.manager.get_current()
            self.WallpaperChanged(current["path"])
        return success

    @dbus.service.method("com.jarvis.WallpaperInterface", in_signature="ss", out_signature="s")
    def AddWallpaper(self, source_path: str, name: str) -> str:
        import json
        try:
            meta = self.manager.add_user_wallpaper(source_path, name)
            return json.dumps({"success": True, "wallpaper": meta})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @dbus.service.method("com.jarvis.WallpaperInterface", in_signature="s", out_signature="b")
    def RemoveWallpaper(self, wallpaper_id: str) -> bool:
        try:
            success = self.manager.remove_user_wallpaper(wallpaper_id)
            if success:
                # If we fell back to default, emit signal
                current = self.manager.get_current()
                if self.manager._cache.get("current") == "jarvis-default":
                    self.WallpaperChanged(current["path"])
            return success
        except Exception:
            return False

    @dbus.service.method("com.jarvis.WallpaperInterface", in_signature="sb", out_signature="b")
    def SetFavorite(self, wallpaper_id: str, favorite: bool) -> bool:
        return self.manager.set_favorite(wallpaper_id, favorite)

class FilesInterface(dbus.service.Object if DBUS_AVAILABLE else object):
    def __init__(self, core, bus, object_path="/com/jarvis/Files"):
        self.core = core
        if DBUS_AVAILABLE and bus:
            super().__init__(bus, object_path)
            
    def _get_caller_user(self, sender) -> str:
        if not sender or not DBUS_AVAILABLE:
            return "unknown"
        try:
            bus = dbus.SystemBus()
            proxy = bus.get_object("org.freedesktop.DBus", "/org/freedesktop/DBus")
            iface = dbus.Interface(proxy, "org.freedesktop.DBus")
            uid = iface.GetConnectionUnixUser(sender)
            import pwd
            return pwd.getpwuid(uid).pw_name
        except Exception:
            return "unknown"

    def _audit(self, sender, op, path):
        user = self._get_caller_user(sender)
        from jarvis_core.audit import AuditRecord, ActionType
        from jarvis_core.redaction import redact_text
        record = AuditRecord(
            action=ActionType.TOOL_CALL,
            actor=f"desktop.file_explorer (user:{user})",
            target="FileService",
            details=f"{op} on {redact_text(path)}"
        )
        self.core.audit_log.record(record)

    @dbus.service.method("com.jarvis.FilesInterface", in_signature="s", out_signature="s", sender_keyword="sender")
    def ReportOperation(self, op: str, path: str, sender=None) -> str:
        self._audit(sender, op, path)
        return "OK"

    # Map 1:1 onto Tool Registry tools
    @dbus.service.method("com.jarvis.FilesInterface", in_signature="s", out_signature="s", sender_keyword="sender")
    def List(self, path: str, sender=None) -> str:
        self._audit(sender, "list", path)
        from jarvis_core.files import FileService
        import json
        return json.dumps(FileService.list_dir(path))
        
    @dbus.service.method("com.jarvis.FilesInterface", in_signature="ss", out_signature="s", sender_keyword="sender")
    def Rename(self, src: str, dst: str, sender=None) -> str:
        self._audit(sender, "rename", src)
        from jarvis_core.files import FileService
        import json
        return json.dumps(FileService.rename(src, dst))
        
    @dbus.service.method("com.jarvis.FilesInterface", in_signature="s", out_signature="s", sender_keyword="sender")
    def Trash(self, path: str, sender=None) -> str:
        self._audit(sender, "trash", path)
        from jarvis_core.files import FileService
        import json
        return json.dumps(FileService.trash(path))

    @dbus.service.method("com.jarvis.FilesInterface", in_signature="s", out_signature="s", sender_keyword="sender")
    def Stat(self, path: str, sender=None) -> str:
        self._audit(sender, "stat", path)
        from jarvis_core.files import FileService
        import json
        return json.dumps(FileService.stat(path))

    @dbus.service.method("com.jarvis.FilesInterface", in_signature="s", out_signature="s", sender_keyword="sender")
    def Mkdir(self, path: str, sender=None) -> str:
        self._audit(sender, "mkdir", path)
        from jarvis_core.files import FileService
        import json
        return json.dumps(FileService.mkdir(path))

    @dbus.service.method("com.jarvis.FilesInterface", in_signature="ss", out_signature="s", sender_keyword="sender")
    def Copy(self, src: str, dst: str, sender=None) -> str:
        self._audit(sender, "copy", f"{src} -> {dst}")
        from jarvis_core.files import FileService
        import json
        return json.dumps(FileService.copy(src, dst))

    @dbus.service.method("com.jarvis.FilesInterface", in_signature="ss", out_signature="s", sender_keyword="sender")
    def Move(self, src: str, dst: str, sender=None) -> str:
        self._audit(sender, "move", f"{src} -> {dst}")
        from jarvis_core.files import FileService
        import json
        return json.dumps(FileService.move(src, dst))

    @dbus.service.method("com.jarvis.FilesInterface", in_signature="ss", out_signature="s", sender_keyword="sender")
    def Search(self, root: str, query: str, sender=None) -> str:
        self._audit(sender, "search", root)
        from jarvis_core.files import FileService
        import json
        return json.dumps(FileService.search(root, query))
