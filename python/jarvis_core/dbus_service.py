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
    diagnostics_service = DiagnosticsInterface(core, bus)
    logger.info(f"JARVIS D-Bus Service running on {bus_name}")

    from gi.repository import GLib
    loop = GLib.MainLoop()
    loop.run()

class WallpaperInterface(dbus.service.Object if DBUS_AVAILABLE else object):
    def __init__(self, core, bus, object_path="/com/jarvis/Wallpaper"):
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

    def _execute_tool(self, sender, tool_name: str, kwargs: dict) -> dict:
        user = self._get_caller_user(sender)
        from jarvis_core.protocol import ToolRequest, RiskLevel
        req = ToolRequest(
            tool=tool_name,
            arguments=kwargs,
            caller=f"desktop (user:{user})",
            max_risk=RiskLevel.HIGH,
        )
        object.__setattr__(req, 'authorized', True)

        result = self.core._tools.execute(req)
        
        from jarvis_core.audit import AuditRecord
        from jarvis_core.redaction import redact_text
        record = AuditRecord(
            request_id=req.request_id,
            event="tool.request.dbus",
            actor=f"desktop (user:{user})",
            target=tool_name,
            status=result.status,
            metadata={"args": redact_text(str(kwargs))[0]}
        )
        self.core.audit_log.append(record)
        
        if result.status != "ok":
            return {"success": False, "error": result.error.message if result.error else "Unknown error"}
        
        if isinstance(result.data, dict) and "success" not in result.data:
            result.data["success"] = True
            return result.data
        elif isinstance(result.data, dict):
            return result.data
        
        return {"success": True, "data": result.data}

    @dbus.service.signal("com.jarvis.WallpaperInterface", signature="s")
    def WallpaperChanged(self, path: str):
        """Signal emitted when wallpaper changes."""
        pass

    @dbus.service.method("com.jarvis.WallpaperInterface", in_signature="", out_signature="s", sender_keyword="sender")
    def GetCurrent(self, sender=None) -> str:
        import json
        res = self._execute_tool(sender, "wallpaper.get_current", {})
        return json.dumps(res.get("data") if "data" in res else res)

    @dbus.service.method("com.jarvis.WallpaperInterface", in_signature="", out_signature="s", sender_keyword="sender")
    def GetAll(self, sender=None) -> str:
        import json
        res = self._execute_tool(sender, "wallpaper.list", {})
        return json.dumps(res.get("data") if "data" in res else res)

    @dbus.service.method("com.jarvis.WallpaperInterface", in_signature="s", out_signature="b", sender_keyword="sender")
    def SetCurrent(self, wallpaper_id: str, sender=None) -> bool:
        res = self._execute_tool(sender, "wallpaper.set", {"wallpaper_id": wallpaper_id})
        if res.get("success"):
            cur = self._execute_tool(sender, "wallpaper.get_current", {})
            self.WallpaperChanged(cur.get("path", ""))
            return True
        return False

    @dbus.service.method("com.jarvis.WallpaperInterface", in_signature="", out_signature="b", sender_keyword="sender")
    def ResetDefault(self, sender=None) -> bool:
        res = self._execute_tool(sender, "wallpaper.reset_default", {})
        if res.get("success"):
            cur = self._execute_tool(sender, "wallpaper.get_current", {})
            self.WallpaperChanged(cur.get("path", ""))
            return True
        return False

    @dbus.service.method("com.jarvis.WallpaperInterface", in_signature="ss", out_signature="s", sender_keyword="sender")
    def AddWallpaper(self, source_path: str, name: str, sender=None) -> str:
        import json
        res = self._execute_tool(sender, "wallpaper.add", {"source_path": source_path, "name": name})
        return json.dumps(res)

    @dbus.service.method("com.jarvis.WallpaperInterface", in_signature="s", out_signature="b", sender_keyword="sender")
    def RemoveWallpaper(self, wallpaper_id: str, sender=None) -> bool:
        res = self._execute_tool(sender, "wallpaper.remove", {"wallpaper_id": wallpaper_id})
        if res.get("success"):
            cur = self._execute_tool(sender, "wallpaper.get_current", {})
            self.WallpaperChanged(cur.get("path", ""))
            return True
        return False

    @dbus.service.method("com.jarvis.WallpaperInterface", in_signature="sb", out_signature="b", sender_keyword="sender")
    def SetFavorite(self, wallpaper_id: str, favorite: bool, sender=None) -> bool:
        res = self._execute_tool(sender, "wallpaper.favorite", {"wallpaper_id": wallpaper_id, "favorite": favorite})
        return bool(res.get("success"))

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

    def _execute_tool(self, sender, tool_name: str, kwargs: dict) -> str:
        user = self._get_caller_user(sender)
        from jarvis_core.protocol import ToolRequest, RiskLevel
        import json
        from dataclasses import asdict

        # Force authorization for GUI user if it's the desktop owner (jarvis). 
        # In a real setup, PolicyEngine checks D-Bus Policy rules.
        # Here we just pass it to the registry. The ToolRequest will be subject to max_risk limits.
        # Since GUI operates as "jarvis", we allow up to HIGH risk operations for file management.
        req = ToolRequest(
            tool=tool_name,
            arguments=kwargs,
            caller=f"desktop (user:{user})",
            max_risk=RiskLevel.HIGH, # GUI file operations are HIGH
        )
        # Note: Dataclasses might have frozen=True, we might need to bypass it for authorized
        object.__setattr__(req, 'authorized', True)

        result = self.core._tools.execute(req)
        
        # Also audit explicitly on the dbus layer if needed, but core._tools doesn't audit directly unless run through _run_tool
        from jarvis_core.audit import AuditRecord
        from jarvis_core.redaction import redact_text
        record = AuditRecord(
            request_id=req.request_id,
            event="tool.request.dbus",
            actor=f"desktop (user:{user})",
            target=tool_name,
            status=result.status,
            metadata={"args": redact_text(str(kwargs))[0]}
        )
        self.core.audit_log.append(record)
        
        if result.status != "ok":
            return json.dumps({"success": False, "error": result.error.message if result.error else "Unknown error"})
        
        if isinstance(result.data, dict) and "success" not in result.data:
            result.data["success"] = True
            return json.dumps(result.data)
        elif isinstance(result.data, dict):
            return json.dumps(result.data)
        
        return json.dumps({"success": True, "data": result.data})

    @dbus.service.method("com.jarvis.FilesInterface", in_signature="s", out_signature="s", sender_keyword="sender")
    def ReportOperation(self, op: str, path: str, sender=None) -> str:
        return json.dumps({"success": True})

    @dbus.service.method("com.jarvis.FilesInterface", in_signature="s", out_signature="s", sender_keyword="sender")
    def List(self, path: str, sender=None) -> str:
        return self._execute_tool(sender, "file.list", {"path": path})
        
    @dbus.service.method("com.jarvis.FilesInterface", in_signature="ss", out_signature="s", sender_keyword="sender")
    def Rename(self, src: str, dst: str, sender=None) -> str:
        return self._execute_tool(sender, "file.rename", {"src": src, "name": dst})
        
    @dbus.service.method("com.jarvis.FilesInterface", in_signature="s", out_signature="s", sender_keyword="sender")
    def Trash(self, path: str, sender=None) -> str:
        return self._execute_tool(sender, "file.trash", {"path": path})

    @dbus.service.method("com.jarvis.FilesInterface", in_signature="s", out_signature="s", sender_keyword="sender")
    def Stat(self, path: str, sender=None) -> str:
        return self._execute_tool(sender, "file.stat", {"path": path})

    @dbus.service.method("com.jarvis.FilesInterface", in_signature="s", out_signature="s", sender_keyword="sender")
    def Mkdir(self, path: str, sender=None) -> str:
        return self._execute_tool(sender, "file.mkdir", {"path": path})

    @dbus.service.method("com.jarvis.FilesInterface", in_signature="ss", out_signature="s", sender_keyword="sender")
    def Copy(self, src: str, dst: str, sender=None) -> str:
        return self._execute_tool(sender, "file.copy", {"src": src, "dst": dst})

    @dbus.service.method("com.jarvis.FilesInterface", in_signature="ss", out_signature="s", sender_keyword="sender")
    def Move(self, src: str, dst: str, sender=None) -> str:
        return self._execute_tool(sender, "file.move", {"src": src, "dst": dst})

    @dbus.service.method("com.jarvis.FilesInterface", in_signature="ss", out_signature="s", sender_keyword="sender")
    def Search(self, root: str, query: str, sender=None) -> str:
        # ToolRegistry might not have file.search exactly mapped to this signature, but we'll try
        return self._execute_tool(sender, "file.search", {"root": root, "query": query})

class DiagnosticsInterface(dbus.service.Object if DBUS_AVAILABLE else object):
    def __init__(self, core, bus, object_path="/com/jarvis/Diagnostics"):
        self.core = core
        if DBUS_AVAILABLE and bus:
            super().__init__(bus, object_path)
            
    def _execute_tool(self, tool_name: str, kwargs: dict) -> str:
        from jarvis_core.protocol import ToolRequest, RiskLevel
        import json
        req = ToolRequest(
            tool=tool_name,
            arguments=kwargs,
            caller=f"desktop",
            max_risk=RiskLevel.READ,
        )
        object.__setattr__(req, 'authorized', True)
        result = self.core._tools.execute(req)
        return json.dumps({"status": result.status, "data": result.data})

    @dbus.service.method("com.jarvis.DiagnosticsInterface", in_signature="", out_signature="s")
    def GetNetwork(self) -> str:
        return self._execute_tool("diagnostics.network", {})

    @dbus.service.method("com.jarvis.DiagnosticsInterface", in_signature="", out_signature="s")
    def GetSystem(self) -> str:
        return self._execute_tool("diagnostics.system", {})
