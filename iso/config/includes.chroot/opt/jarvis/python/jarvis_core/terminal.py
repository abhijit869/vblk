"""Controlled terminal execution for JARVIS."""

from __future__ import annotations

import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from jarvis_core.protocol import RiskLevel
from jarvis_core.redaction import redact_text


READ_ONLY_COMMANDS = {
    "cat",
    "date",
    "df",
    "du",
    "free",
    "head",
    "id",
    "journalctl",
    "ls",
    "lscpu",
    "nproc",
    "pwd",
    "ps",
    "tail",
    "uname",
    "uptime",
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

# Commands that print file contents. Reading credential material is treated as
# HIGH risk because the output may be forwarded to an AI provider.
CONTENT_READERS = {"cat", "head", "tail"}

SENSITIVE_PATH_PATTERNS = [
    re.compile(r"^/etc/(g?shadow|sudoers)(\.d/.*)?$"),
    re.compile(r"^/proc/[^/]+/environ$"),
    re.compile(r"(^|/)\.ssh(/|$)"),
    re.compile(r"(^|/)\.gnupg(/|$)"),
    re.compile(r"(^|/)\.env(\..*)?$"),
    re.compile(r"(^|/)id_(rsa|dsa|ecdsa|ed25519)[^/]*$"),
    re.compile(r"\.(pem|key|p12|pfx)$"),
    re.compile(r"(^|/)(\.netrc|\.pgpass|credentials(\.json)?)$"),
]

IP_READ_ONLY_OBJECTS = {"a", "addr", "address", "l", "link", "r", "route", "n", "neigh", "neighbour", "rule", "maddr"}
IP_READ_ONLY_VERBS = {"show", "list", "lst", "ls", "get"}


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


class TerminalEngine:
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
        start = monotonic()

        if risk > max_risk:
            return TerminalResult(
                command=argv,
                risk=risk,
                stdout="",
                stderr=f"Denied command risk {risk.name}; max allowed is {max_risk.name}",
                exit_code=None,
                signal=None,
                duration_ms=0,
                cwd=resolved_cwd,
                timed_out=False,
                truncated=False,
                redacted=False,
                denied=True,
            )

        try:
            completed = subprocess.run(
                argv,
                cwd=resolved_cwd,
                capture_output=True,
                text=True,
                timeout=timeout_ms / 1000,
                check=False,
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
        )

    def _parse_command(self, command: str | list[str]) -> list[str]:
        argv = shlex.split(command) if isinstance(command, str) else [str(part) for part in command]
        if not argv:
            raise ValueError("terminal command is empty")
        return argv


def classify_command(argv: list[str], cwd: str | Path | None = None) -> RiskLevel:
    if not argv:
        return RiskLevel.LOW
    executable = Path(argv[0]).name
    if executable in HIGH_COMMANDS:
        return RiskLevel.HIGH
    if executable == "systemctl":
        return RiskLevel.READ if _is_read_only_systemctl(argv) else RiskLevel.MEDIUM
    if executable == "ip":
        return RiskLevel.READ if _is_read_only_ip(argv) else RiskLevel.MEDIUM
    if executable in MEDIUM_COMMANDS:
        return RiskLevel.MEDIUM
    if executable in READ_ONLY_COMMANDS:
        if executable in CONTENT_READERS and _touches_sensitive_path(argv[1:], cwd):
            return RiskLevel.HIGH
        if executable == "journalctl" and any(
            arg.startswith(("--vacuum", "--rotate", "--flush", "--sync", "--relinquish")) for arg in argv[1:]
        ):
            return RiskLevel.MEDIUM
        if executable == "date" and any(arg in {"-s"} or arg.startswith("--set") for arg in argv[1:]):
            return RiskLevel.MEDIUM
        return RiskLevel.READ
    return RiskLevel.MEDIUM


def _is_read_only_systemctl(argv: list[str]) -> bool:
    read_only_subcommands = {"list-units", "list-unit-files", "status", "is-active", "is-enabled", "is-failed", "show"}
    return len(argv) >= 2 and argv[1] in read_only_subcommands


def _is_read_only_ip(argv: list[str]) -> bool:
    args = [arg for arg in argv[1:] if not arg.startswith("-")]
    if not args:
        return False
    if args[0] not in IP_READ_ONLY_OBJECTS:
        return False
    return len(args) == 1 or args[1] in IP_READ_ONLY_VERBS


def _touches_sensitive_path(args: list[str], cwd: str | Path | None) -> bool:
    base = Path(cwd) if cwd is not None else Path.cwd()
    for arg in args:
        if arg.startswith("-"):
            continue
        candidates = {arg}
        try:
            candidates.add(str((base / Path(arg).expanduser()).resolve()))
        except (OSError, RuntimeError):
            pass
        if any(pattern.search(candidate) for candidate in candidates for pattern in SENSITIVE_PATH_PATTERNS):
            return True
    return False


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
