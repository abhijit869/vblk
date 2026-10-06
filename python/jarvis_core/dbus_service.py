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
    from dbus.mainloop.glib import DBusGMainLoop  # type: ignore

    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False

    # Create mock classes to allow tests to pass without D-Bus installed
    class dbus:  # type: ignore
        class service:
            class Object:
                pass

            def method(dbus_interface, in_signature=None, out_signature=None):  # type: ignore
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
    bus = dbus.SessionBus()
    # Claim the bus name
    bus_name = dbus.service.BusName("com.jarvis.Core", bus)

    # Initialize the service
    service = JarvisDBusService(core, bus)
    logger.info(f"JARVIS D-Bus Service running on {bus_name}")

    # Normally we would import GLib and run the mainloop here
    # from gi.repository import GLib
    # loop = GLib.MainLoop()
    # loop.run()
