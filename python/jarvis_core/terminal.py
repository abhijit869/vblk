"""Controlled terminal execution for JARVIS.

Security model (deny by default):

1. The command is parsed into an argument list; no shell is ever involved.
2. The executable must be a known command resolved from trusted system
   directories. Unknown programs, interpreters, shells, privilege-escalation and
   "wrapper" programs (``sudo``, ``env``, ``xargs``, ``find -exec`` ...) are
   classified CRITICAL and are never executed.
3. Every argument is checked against the shared sensitive-path guard.
4. The risk level is compared with the caller's ``max_risk``.
5. The command runs inside the bubblewrap sandbox (see ``sandbox.py``) with a
   scrubbed environment, a timeout and an output limit; output is redacted.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from jarvis_core.pathguard import (
    SENSITIVE_PATH_PATTERNS,
    is_sensitive_path,
    touches_sensitive_path,
)
from jarvis_core.permissions import PermissionEngine
from jarvis_core.protocol import RiskLevel
from jarvis_core.redaction import redact_text
from jarvis_core.sandbox import SAFE_ENV, SandboxEngine, SandboxUnavailable

# Executables are only ever resolved from these directories.
TRUSTED_BIN_DIRS = ("/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin")

READ_ONLY_COMMANDS = {
    "cat",
    "date",
    "df",
    "du",
    "echo",
    "free",
    "head",
    "hostname",
    "id",
    "journalctl",
    "ls",
    "lsblk",
    "lscpu",
    "nproc",
    "pwd",
    "ps",
    "stat",
    "tail",
    "uname",
    "uptime",
    "wc",
    "whoami",
}

MEDIUM_COMMANDS = {
    "apt",
    "apt-get",
    "dnf",
    "ip",
    "kill",
    "pkill",
    "systemctl",
}

HIGH_COMMANDS = {
    "chmod",
    "chown",
    "dd",
    "fdisk",
    "mkfs",
    "mount",
    "mv",
    "rm",
    "shred",
    "umount",
}

# Never executed, regardless of max_risk: they run arbitrary code, escalate
# privileges, wrap another command (hiding it from classification) or open
# network channels.
FORBIDDEN_COMMANDS = {
    # privilege escalation
    "sudo",
    "su",
    "doas",
    "pkexec",
    "run0",
    "runuser",
    "setpriv",
    "capsh",
    "chroot",
    "nsenter",
    "unshare",
    # shells & interpreters
    "sh",
    "bash",
    "dash",
    "zsh",
    "ksh",
    "csh",
    "tcsh",
    "fish",
    "busybox",
    "toybox",
    "python",
    "python2",
    "python3",
    "perl",
    "ruby",
    "node",
    "nodejs",
    "deno",
    "bun",
    "php",
    "lua",
    "tclsh",
    "awk",
    "gawk",
    "mawk",
    "nawk",
    "sed",
    "vim",
    "vi",
    "nvim",
    "emacs",
    "ed",
    "less",
    "more",
    "man",
    # command wrappers
    "env",
    "xargs",
    "find",
    "nohup",
    "timeout",
    "nice",
    "ionice",
    "setsid",
    "stdbuf",
    "time",
    "watch",
    "strace",
    "ltrace",
    "gdb",
    "script",
    "expect",
    "parallel",
    "flock",
    "taskset",
    "chrt",
    # network & exfiltration
    "curl",
    "wget",
    "nc",
    "ncat",
    "netcat",
    "socat",
    "telnet",
    "ssh",
    "scp",
    "sftp",
    "rsync",
    "ftp",
    "tftp",
    "openssl",
    "nmap",
    # persistence / system modification
    "crontab",
    "at",
    "batch",
    "systemd-run",
    "insmod",
    "rmmod",
    "modprobe",
    "kexec",
    "iptables",
    "nft",
    "ufw",
    "useradd",
    "usermod",
    "userdel",
    "passwd",
    "chpasswd",
    "visudo",
    "tee",
    "cp",
    "install",
    "ln",
    "dpkg",
    "make",
    "gcc",
    "cc",
    "git",
}

# Read-only commands whose output is file contents.
CONTENT_READERS = {"cat", "head", "tail", "wc"}

# Flags that turn an otherwise read-only command into something riskier.
DANGEROUS_FLAGS: dict[str, tuple[tuple[str, RiskLevel], ...]] = {
    "du": (("--files0-from", RiskLevel.HIGH),),
    "wc": (("--files0-from", RiskLevel.HIGH),),
    "journalctl": (
        ("--vacuum", RiskLevel.MEDIUM),
        ("--rotate", RiskLevel.MEDIUM),
        ("--flush", RiskLevel.MEDIUM),
        ("--sync", RiskLevel.MEDIUM),
        ("--relinquish", RiskLevel.MEDIUM),
        ("--setup-keys", RiskLevel.HIGH),
        ("--update-catalog", RiskLevel.MEDIUM),
    ),
    "date": (("-s", RiskLevel.MEDIUM), ("--set", RiskLevel.MEDIUM)),
    "ps": (
        ("e", RiskLevel.HIGH),
    ),  # BSD-style 'e' prints process environments (may contain secrets)
}

APT_READ_ONLY = {
    "list",
    "show",
    "search",
    "policy",
    "depends",
    "rdepends",
    "changelog",
    "madison",
}
APT_HIGH = {
    "install",
    "remove",
    "purge",
    "autoremove",
    "full-upgrade",
    "dist-upgrade",
    "reinstall",
    "build-dep",
    "source",
    "download",
}

IP_READ_ONLY_OBJECTS = {
    "a",
    "addr",
    "address",
    "l",
    "link",
    "r",
    "route",
    "n",
    "neigh",
    "neighbour",
    "rule",
    "maddr",
}
IP_READ_ONLY_VERBS = {"show", "list", "lst", "ls", "get"}

__all__ = [
    "SENSITIVE_PATH_PATTERNS",
    "TerminalEngine",
    "TerminalResult",
    "classify_command",
    "resolve_executable",
]


@dataclass(frozen=True)
class TerminalResult:
    command: list[str]
    risk: RiskLevel
    stdout: str
    stderr: str
    exit_code: int | None
    signal: int | None
    duration_ms: int
    cwd: str
    timed_out: bool
    truncated: bool
    redacted: bool
    denied: bool = False
    sandboxed: bool = False


class TerminalEngine:
    def __init__(
        self,
        sandbox: SandboxEngine | None = None,
        permissions: PermissionEngine | None = None,
    ) -> None:
        self._sandbox = sandbox
        self._permissions = permissions

    @property
    def sandbox(self) -> SandboxEngine:
        if self._sandbox is None:
            self._sandbox = SandboxEngine()
        return self._sandbox

    def execute(
        self,
        command: str | list[str],
        cwd: str | Path = ".",
        timeout_ms: int = 2000,
        output_limit_bytes: int = 32768,
        max_risk: RiskLevel = RiskLevel.READ,
    ) -> TerminalResult:
        argv = self._parse_command(command)
        resolved_cwd = str(Path(cwd).resolve())
        risk = classify_command(argv, cwd=resolved_cwd)

        def deny(reason: str) -> TerminalResult:
            return TerminalResult(
                command=argv,
                risk=risk,
                stdout="",
                stderr=reason,
                exit_code=None,
                signal=None,
                duration_ms=0,
                cwd=resolved_cwd,
                timed_out=False,
                truncated=False,
                redacted=False,
                denied=True,
            )

        if risk >= RiskLevel.CRITICAL:
            return deny(
                f"Denied command risk {risk.name}: '{Path(argv[0]).name}' is not an allowed command"
            )
        if risk > max_risk:
            return deny(
                f"Denied command risk {risk.name}; max allowed is {max_risk.name}"
            )
        if not Path(resolved_cwd).is_dir():
            return deny(f"Denied: working directory does not exist: {resolved_cwd}")
        if is_sensitive_path(resolved_cwd):
            return deny("Denied: working directory is a sensitive location")

        executable = resolve_executable(argv[0])
        if executable is None:
            return deny(
                f"Denied: '{argv[0]}' was not found in trusted system directories"
            )
        exec_argv = [executable, *argv[1:]]

        sandboxed = False
        try:
            if self.sandbox.available:
                allow_net, rw_paths = (False, [])
                if risk > RiskLevel.READ and self._permissions is not None:
                    allow_net, rw_paths = self._permissions.get_sandbox_config()
                exec_argv = self.sandbox.wrap_command(
                    exec_argv,
                    allow_network=allow_net,
                    rw_paths=[p for p in rw_paths if os.path.isdir(p)],
                    # 'ps' needs to see host processes; everything else gets its own PID namespace.
                    isolate_pid=Path(argv[0]).name != "ps",
                )
                sandboxed = True
            elif self.sandbox.mode == "required":
                return deny(
                    "Denied: sandbox is required but bubblewrap is not functional on this system"
                )
            elif self.sandbox.mode == "auto" and risk > RiskLevel.READ:
                return deny(
                    f"Denied: {risk.name} commands require a working sandbox (install bubblewrap)"
                )
        except (SandboxUnavailable, ValueError) as exc:
            return deny(f"Denied: {exc}")

        start = monotonic()
        try:
            completed = subprocess.run(
                exec_argv,
                cwd=resolved_cwd,
                capture_output=True,
                text=True,
                timeout=timeout_ms / 1000,
                check=False,
                env=dict(SAFE_ENV),
                stdin=subprocess.DEVNULL,
            )
            raw_stdout = completed.stdout
            raw_stderr = completed.stderr
            exit_code = completed.returncode if completed.returncode >= 0 else None
            signal = -completed.returncode if completed.returncode < 0 else None
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            raw_stdout = _decode_timeout_output(exc.stdout)
            raw_stderr = _decode_timeout_output(exc.stderr)
            exit_code = None
            signal = None
            timed_out = True

        stdout, stdout_redacted = redact_text(raw_stdout)
        stderr, stderr_redacted = redact_text(raw_stderr)
        stdout, stdout_truncated = _limit_output(stdout, output_limit_bytes)
        stderr, stderr_truncated = _limit_output(stderr, output_limit_bytes)

        return TerminalResult(
            command=argv,
            risk=risk,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            signal=signal,
            duration_ms=int((monotonic() - start) * 1000),
            cwd=resolved_cwd,
            timed_out=timed_out,
            truncated=stdout_truncated or stderr_truncated,
            redacted=stdout_redacted or stderr_redacted,
            sandboxed=sandboxed,
        )

    def _parse_command(self, command: str | list[str]) -> list[str]:
        argv = (
            shlex.split(command)
            if isinstance(command, str)
            else [str(part) for part in command]
        )
        if not argv:
            raise ValueError("terminal command is empty")
        if any("\x00" in part for part in argv):
            raise ValueError("terminal command contains a NUL byte")
        return argv


def resolve_executable(name: str) -> str | None:
    """Resolve ``name`` to an executable inside :data:`TRUSTED_BIN_DIRS`.

    Absolute paths are accepted only if they already point into a trusted
    directory, so ``/tmp/evil/ls`` can never masquerade as ``ls``.
    """
    if "/" in name:
        candidate = Path(name)
        if not candidate.is_absolute():
            return None
        real = os.path.realpath(candidate)
        parent = os.path.dirname(os.path.abspath(candidate))
        if parent not in TRUSTED_BIN_DIRS or not os.access(real, os.X_OK):
            return None
        return str(candidate)
    found = shutil.which(name, path=os.pathsep.join(TRUSTED_BIN_DIRS))
    return found


def classify_command(argv: list[str], cwd: str | Path | None = None) -> RiskLevel:
    if not argv:
        return RiskLevel.CRITICAL
    raw = argv[0]
    executable = Path(raw).name
    args = argv[1:]

    # Programs addressed by a path outside the trusted bin directories are unknown programs.
    if "/" in raw and os.path.dirname(os.path.abspath(raw)) not in TRUSTED_BIN_DIRS:
        return RiskLevel.CRITICAL
    if executable in FORBIDDEN_COMMANDS:
        return RiskLevel.CRITICAL
    if (
        executable.startswith(("python", "perl", "ruby", "php", "lua", "mkfs."))
        and executable not in HIGH_COMMANDS
    ):
        return RiskLevel.HIGH if executable.startswith("mkfs.") else RiskLevel.CRITICAL

    if executable in HIGH_COMMANDS:
        return RiskLevel.HIGH
    if executable == "systemctl":
        return RiskLevel.READ if _is_read_only_systemctl(argv) else RiskLevel.MEDIUM
    if executable == "ip":
        return RiskLevel.READ if _is_read_only_ip(argv) else RiskLevel.MEDIUM
    if executable in {"apt", "apt-get"}:
        sub = next((a for a in args if not a.startswith("-")), "")
        if sub in APT_READ_ONLY:
            return RiskLevel.READ
        return RiskLevel.HIGH if sub in APT_HIGH else RiskLevel.MEDIUM
    if executable in MEDIUM_COMMANDS:
        return RiskLevel.MEDIUM
    if executable in READ_ONLY_COMMANDS:
        risk = RiskLevel.READ
        for flag, flag_risk in DANGEROUS_FLAGS.get(executable, ()):
            if _has_flag(executable, args, flag):
                risk = max(risk, flag_risk)
        if executable == "hostname" and any(not a.startswith("-") for a in args):
            risk = max(risk, RiskLevel.MEDIUM)  # 'hostname NAME' changes the hostname
        if touches_sensitive_path(args, cwd):
            # Reading credential material is HIGH risk because output may be forwarded to an AI provider.
            risk = max(risk, RiskLevel.HIGH)
        return risk
    # Deny by default: anything not explicitly classified is never executed.
    return RiskLevel.CRITICAL


def _has_flag(executable: str, args: list[str], flag: str) -> bool:
    if executable == "ps" and flag == "e":
        # BSD syntax: an argument without a dash containing 'e' (e.g. 'auxe', 'e').
        return any(not a.startswith("-") and "e" in a and a.isalpha() for a in args)
    for arg in args:
        if (
            arg == flag
            or arg.startswith(flag + "=")
            or (flag.startswith("--") and arg.startswith(flag))
        ):
            return True
    return False


def _is_read_only_systemctl(argv: list[str]) -> bool:
    read_only_subcommands = {
        "list-units",
        "list-unit-files",
        "list-timers",
        "list-sockets",
        "status",
        "is-active",
        "is-enabled",
        "is-failed",
        "show",
        "cat",
    }
    args = [a for a in argv[1:] if not a.startswith("-")]
    return bool(args) and args[0] in read_only_subcommands


def _is_read_only_ip(argv: list[str]) -> bool:
    args = [arg for arg in argv[1:] if not arg.startswith("-")]
    if not args:
        return False
    if args[0] not in IP_READ_ONLY_OBJECTS:
        return False
    return len(args) == 1 or args[1] in IP_READ_ONLY_VERBS


def _touches_sensitive_path(args: list[str], cwd: str | Path | None) -> bool:
    """Backward-compatible alias for :func:`jarvis_core.pathguard.touches_sensitive_path`."""
    return touches_sensitive_path(args, cwd)


def _limit_output(value: str, limit_bytes: int) -> tuple[str, bool]:
    encoded = value.encode("utf-8")
    if len(encoded) <= limit_bytes:
        return value, False
    truncated = encoded[:limit_bytes].decode("utf-8", errors="ignore")
    return f"{truncated}\n[TRUNCATED]", True


def _decode_timeout_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
