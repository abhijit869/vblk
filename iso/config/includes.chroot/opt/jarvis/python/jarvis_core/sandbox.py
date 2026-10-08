"""Sandbox Engine for JARVIS OS.

Wraps terminal execution in a restricted environment using Bubblewrap (bwrap).
Ensures AI-executed tools cannot permanently damage the host filesystem unless
explicitly authorized.

Sandbox properties (when bwrap is available):

* the whole host filesystem is mounted read-only;
* credential files (``/etc/shadow``, SSH host keys, JARVIS secrets, ...) are
  masked so they cannot be read even by a root daemon;
* fresh ``/tmp``, ``/dev`` and ``/proc``; ``$HOME`` folders holding secrets are
  hidden behind empty tmpfs mounts;
* new user, IPC, UTS, cgroup and (by default) network and PID namespaces;
* all capabilities dropped, a fresh session (blocks TIOCSTI keystroke
  injection into the controlling terminal), a scrubbed environment;
* the sandbox dies with its parent.

Modes (``JARVIS_SANDBOX`` environment variable):

``required``  Refuse to run anything if bwrap is missing or broken (production).
``auto``      Use bwrap when it works; otherwise only READ-risk commands may run
              unsandboxed (development default).
``off``       Never sandbox (tests / debugging only).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

SANDBOX_MODES = {"required", "auto", "off"}

# Files masked with /dev/null inside the sandbox.
MASKED_FILES = (
    "/etc/shadow",
    "/etc/shadow-",
    "/etc/gshadow",
    "/etc/gshadow-",
    "/etc/sudoers",
    "/etc/security/opasswd",
)

# Directories hidden behind an empty tmpfs inside the sandbox.
MASKED_DIRS = (
    "/root",
    "/etc/sudoers.d",
    "/etc/ssl/private",
    "/etc/jarvis",
    "/var/lib/jarvis",
    "/run/secrets",
    "/run/credentials",
)

# Per-user secret directories hidden inside every home directory.
MASKED_HOME_DIRS = (
    ".ssh",
    ".gnupg",
    ".aws",
    ".azure",
    ".kube",
    ".password-store",
    ".mozilla",
    ".config/google-chrome",
    ".config/chromium",
    ".config/gcloud",
    ".config/gh",
    ".local/share/keyrings",
)

# Paths that may never be bound read-write, whatever the role says.
FORBIDDEN_RW_PATHS = {
    "/",
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
    "/lib",
    "/lib64",
    "/boot",
    "/var",
    "/opt",
    "/opt/jarvis",
    "/root",
    "/proc",
    "/sys",
    "/dev",
    "/run",
}

SAFE_ENV = {
    "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "HOME": "/tmp",
    "TERM": "dumb",
}


class SandboxUnavailable(RuntimeError):
    """Raised when sandboxing is required but bwrap is missing or not functional."""


class SandboxEngine:
    def __init__(self, require_bwrap: bool = False, mode: str | None = None):
        self._bwrap_path = shutil.which("bwrap")
        self.mode = (
            mode
            or os.environ.get("JARVIS_SANDBOX")
            or ("required" if require_bwrap else "auto")
        ).lower()
        if self.mode not in SANDBOX_MODES:
            raise ValueError(
                f"invalid sandbox mode {self.mode!r}; expected one of {sorted(SANDBOX_MODES)}"
            )
        if self.mode == "required" and not self._bwrap_path:
            raise SandboxUnavailable(
                "Bubblewrap (bwrap) is not installed but sandboxing is required."
            )
        self._functional: bool | None = None

    @property
    def available(self) -> bool:
        """True if bwrap is installed and can actually create a sandbox here."""
        if self.mode == "off" or not self._bwrap_path:
            return False
        if self._functional is None:
            self._functional = self._probe()
        return self._functional

    def _probe(self) -> bool:
        try:
            probe = subprocess.run(
                self._build_bwrap_args(
                    allow_network=False, rw_paths=None, isolate_pid=True
                )
                + ["/bin/true"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            return probe.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def wrap_command(
        self,
        cmd: list[str] | str,
        allow_network: bool = False,
        rw_paths: list[str] | None = None,
        isolate_pid: bool = True,
    ) -> list[str]:
        """Wrap a command in a bwrap sandbox.

        String commands are *not* passed to a shell; they are rejected so shell
        syntax can never reach the host.
        """
        if isinstance(cmd, str):
            raise ValueError(
                "sandboxed commands must be an argument list, not a shell string"
            )
        if not cmd:
            raise ValueError("empty command")

        if not self._bwrap_path or self.mode == "off":
            if self.mode == "required":
                raise SandboxUnavailable("sandbox required but bwrap is unavailable")
            # Fallback if bwrap is missing in development environments
            return list(cmd)

        return self._build_bwrap_args(allow_network, rw_paths, isolate_pid) + [
            "--",
            *cmd,
        ]

    def _build_bwrap_args(
        self, allow_network: bool, rw_paths: list[str] | None, isolate_pid: bool
    ) -> list[str]:
        assert self._bwrap_path is not None
        args = [
            self._bwrap_path,
            "--ro-bind",
            "/",
            "/",  # Make entire host OS read-only
            "--dev",
            "/dev",  # Minimal private /dev
            "--proc",
            "/proc",  # Fresh /proc
            "--tmpfs",
            "/tmp",  # Provide a volatile /tmp that disappears after execution
            "--tmpfs",
            "/var/tmp",
            "--tmpfs",
            "/dev/shm",
            "--unshare-user-try",
            "--unshare-ipc",
            "--unshare-uts",
            "--unshare-cgroup-try",
            "--hostname",
            "jarvis-sandbox",
            "--new-session",  # Blocks TIOCSTI injection into the parent terminal
            "--die-with-parent",
            "--cap-drop",
            "ALL",
            "--clearenv",
        ]
        for key, value in SAFE_ENV.items():
            args.extend(["--setenv", key, value])
        if isolate_pid:
            args.append("--unshare-pid")
        if not allow_network:
            args.append("--unshare-net")  # Disconnect from the network

        for path in MASKED_FILES:
            if os.path.isfile(path):
                args.extend(["--ro-bind", "/dev/null", path])
        for path in MASKED_DIRS:
            if os.path.isdir(path):
                args.extend(["--tmpfs", path])
        for home in _home_dirs():
            for sub in MASKED_HOME_DIRS:
                target = home / sub
                if target.is_dir():
                    args.extend(["--tmpfs", str(target)])

        for path in validate_rw_paths(rw_paths or []):
            args.extend(["--bind", path, path])
        return args


def validate_rw_paths(paths: list[str]) -> list[str]:
    """Return normalised writable paths, refusing system locations."""
    validated: list[str] = []
    for raw in paths:
        if not isinstance(raw, str) or not raw.startswith("/"):
            raise ValueError(f"writable sandbox path must be absolute: {raw!r}")
        normalised = os.path.normpath(raw)
        if normalised in FORBIDDEN_RW_PATHS:
            raise ValueError(
                f"refusing to make {normalised} writable inside the sandbox"
            )
        validated.append(normalised)
    return validated


def _home_dirs() -> list[Path]:
    homes: list[Path] = []
    for base in (Path("/home"),):
        try:
            homes.extend(p for p in base.iterdir() if p.is_dir())
        except OSError:
            continue
    return homes
