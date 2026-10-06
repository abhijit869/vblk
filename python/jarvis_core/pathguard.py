"""Filesystem access guard shared by every JARVIS tool that touches paths.

All tool output may be forwarded to a cloud AI provider, so credential
material must never be readable through *any* tool (file.read, file.search,
terminal.execute, ...). This module is the single source of truth for which
paths are off-limits.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Paths whose *contents* must never be exposed.
SENSITIVE_PATH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^/etc/(g?shadow|sudoers|security/opasswd)(-|\.d(/.*)?)?$"),
    re.compile(r"^/etc/ssh/ssh_host_[^/]*_key$"),
    re.compile(r"^/etc/(ssl/private|jarvis/secrets?)(/|$)"),
    re.compile(r"^/etc/jarvis/[^/]*\.env$"),
    re.compile(r"^/var/lib/jarvis/(keys|integrity\.key|audit\.key)(/|$)"),
    re.compile(r"^/(root)(/|$)"),
    re.compile(r"^/proc/[^/]+/(environ|mem|maps|smaps|auxv|cmdline|fd(/|$))"),
    re.compile(r"^/proc/(kcore|kallsyms|keys|key-users)$"),
    re.compile(r"^/sys/firmware(/|$)"),
    re.compile(r"^/dev/(mem|kmem|port|sd[a-z]|nvme|vd[a-z]|xvd|mapper|disk|input)"),
    re.compile(r"^/run/(secrets|credentials)(/|$)"),
    re.compile(r"(^|/)\.ssh(/|$)"),
    re.compile(r"(^|/)\.gnupg(/|$)"),
    re.compile(r"(^|/)\.password-store(/|$)"),
    re.compile(r"(^|/)\.aws(/|$)"),
    re.compile(r"(^|/)\.azure(/|$)"),
    re.compile(r"(^|/)\.kube(/|$)"),
    re.compile(r"(^|/)\.docker/config\.json$"),
    re.compile(r"(^|/)\.config/(gcloud|gh|hub|op|rclone)(/|$)"),
    re.compile(r"(^|/)\.(mozilla|thunderbird)(/|$)"),
    re.compile(
        r"(^|/)\.config/(google-chrome|chromium|BraveSoftware|microsoft-edge)(/|$)"
    ),
    re.compile(r"(^|/)\.local/share/keyrings(/|$)"),
    re.compile(r"(^|/)\.env(\..*)?$"),
    re.compile(r"(^|/)id_(rsa|dsa|ecdsa|ed25519)[^/]*$"),
    re.compile(r"\.(pem|key|p12|pfx|jks|keystore|kdbx|gpg|asc)$"),
    re.compile(
        r"(^|/)(\.netrc|\.pgpass|\.git-credentials|\.npmrc|\.pypirc|credentials(\.json)?)$"
    ),
    re.compile(
        r"(^|/)(\.bash_history|\.zsh_history|\.python_history|\.mysql_history|\.psql_history)$"
    ),
    re.compile(r"(^|/)\.git/config$"),
)

# Pseudo-filesystems that should not be read through generic file tools.
BLOCKED_PREFIXES: tuple[str, ...] = ("/dev/", "/proc/", "/sys/")

MAX_FILE_READ_BYTES = 256 * 1024


class PathDenied(PermissionError):
    """Raised when a path is outside what JARVIS tools may access."""


def _candidates(raw: str, base: Path) -> set[str]:
    candidates = {raw}
    try:
        expanded = Path(raw).expanduser()
        candidates.add(str(expanded))
        resolved = (base / expanded).resolve()
        candidates.add(str(resolved))
    except (OSError, RuntimeError, ValueError):
        pass
    return candidates


def is_sensitive_path(raw: str, cwd: str | Path | None = None) -> bool:
    """Return True if ``raw`` (literal, expanded or symlink-resolved) is credential material."""
    base = Path(cwd) if cwd is not None else Path.cwd()
    return any(
        pattern.search(candidate)
        for candidate in _candidates(raw, base)
        for pattern in SENSITIVE_PATH_PATTERNS
    )


def touches_sensitive_path(args: list[str], cwd: str | Path | None = None) -> bool:
    """Return True if any argument (including ``--opt=value`` values) names a sensitive path."""
    for arg in args:
        values = [arg]
        if arg.startswith("-"):
            if "=" not in arg:
                continue
            values = [arg.split("=", 1)[1]]
        if any(value and is_sensitive_path(value, cwd) for value in values):
            return True
    return False


def resolve_readable_path(raw: str, cwd: str | Path | None = None) -> Path:
    """Resolve ``raw`` and verify a generic tool may read it.

    Raises :class:`PathDenied` for credential material and pseudo-filesystems.
    """
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        raise PathDenied("invalid path")
    base = Path(cwd) if cwd is not None else Path.cwd()
    resolved = (base / Path(raw).expanduser()).resolve()
    if is_sensitive_path(raw, base) or is_sensitive_path(str(resolved), base):
        raise PathDenied(f"access to sensitive path denied: {resolved}")
    text = str(resolved) + ("/" if resolved.is_dir() else "")
    if any(text.startswith(prefix) for prefix in BLOCKED_PREFIXES):
        raise PathDenied(f"access to pseudo-filesystem denied: {resolved}")
    for root in _allowed_roots():
        if root == Path("/") or resolved == root or root in resolved.parents:
            return resolved
    raise PathDenied(f"path is outside the allowed roots: {resolved}")


def _allowed_roots() -> list[Path]:
    """Roots that generic file tools may access (``JARVIS_FILE_ROOTS``, colon-separated)."""
    configured = os.environ.get("JARVIS_FILE_ROOTS", "")
    if not configured:
        return [Path("/")]
    return [Path(part).resolve() for part in configured.split(":") if part]
