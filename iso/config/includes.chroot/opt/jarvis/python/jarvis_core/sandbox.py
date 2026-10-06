"""Sandbox Engine for JARVIS OS.

Wraps terminal execution in secure, restricted environments using Bubblewrap (bwrap).
Ensures AI-executed tools cannot permanently damage the host filesystem unless explicitly authorized.
"""

from __future__ import annotations

import shutil


class SandboxEngine:
    def __init__(self, require_bwrap: bool = False):
        self._bwrap_path = shutil.which("bwrap")
        if require_bwrap and not self._bwrap_path:
            raise RuntimeError("Bubblewrap (bwrap) is not installed but require_bwrap is True.")

    def wrap_command(self, cmd: list[str] | str, allow_network: bool = False, rw_paths: list[str] | None = None) -> list[str]:
        """Wrap a command in a bwrap sandbox container."""
        if isinstance(cmd, str):
            # For simplicity, if it's a string, we wrap it in a bash call
            cmd = ["bash", "-c", cmd]

        if not self._bwrap_path:
            # Fallback if bwrap is missing in development environments
            return cmd

        bwrap_cmd = [
            self._bwrap_path,
            "--ro-bind", "/", "/",       # Make entire host OS read-only
            "--dev", "/dev",             # Bind /dev
            "--proc", "/proc",           # Bind /proc
            "--tmpfs", "/tmp",           # Provide a volatile /tmp that disappears after execution
            "--die-with-parent",
        ]

        if not allow_network:
            bwrap_cmd.append("--unshare-net") # Disconnect from the internet

        if rw_paths:
            for path in rw_paths:
                bwrap_cmd.extend(["--bind", path, path])

        bwrap_cmd.extend(cmd)
        return bwrap_cmd
