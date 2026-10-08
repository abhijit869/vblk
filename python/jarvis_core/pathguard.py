import os
import re
from pathlib import Path
from typing import Tuple

PROTECTED_SYSTEM_PATHS = [
    "/etc", "/boot", "/usr", "/bin", "/sbin", "/proc", "/sys", "/dev", "/run", "/root",
    "/opt/jarvis", "/var/lib/jarvis", "/var/log/jarvis"
]

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


def _is_tier2(path: Path) -> bool:
    try:
        home = Path.home().resolve()
    except Exception:
        home = Path("/nonexistent_home")
        
    s = str(path)
    # Prefix check using is_relative_to for absolute certainty
    for p in PROTECTED_SYSTEM_PATHS:
        if path.is_relative_to(Path(p)):
            return True
            
    # lib*
    if path.is_relative_to(Path("/lib")) or path.is_relative_to(Path("/lib64")) or path.is_relative_to(Path("/lib32")) or path.is_relative_to(Path("/libexec")) or path.is_relative_to(Path("/libx32")):
        return True

    # User secrets
    for secret_dir in [".ssh", ".gnupg", ".config/jarvis", ".mozilla", ".config/google-chrome"]:
        if path.is_relative_to(home / secret_dir):
            return True
            
    # Key files
    name = path.name
    if name.endswith(".pem") or name.endswith(".key") or name.startswith("id_"):
        return True
        
    return False


class PathGuard:
    @staticmethod
    def _validate_basic(path: str | Path) -> Tuple[bool, str, Path]:
        s_path = str(path)
        if "\0" in s_path:
            return False, "NUL_BYTE_IN_PATH", Path()
            
        try:
            p = Path(path).expanduser().resolve()
                
            if len(str(p)) > 4096:
                return False, "PATH_TOO_LONG", p
                
            for part in p.parts:
                if len(part) > 255:
                    return False, "COMPONENT_TOO_LONG", p
                    
            return True, "OK", p
        except Exception as e:
            return False, f"INVALID_PATH", Path()

    @staticmethod
    def check_read(path: str | Path, ai_tool_path: bool = False) -> Tuple[bool, str]:
        ok, reason, p = PathGuard._validate_basic(path)
        if not ok:
            return False, reason
            
        try:
            resolved = p.resolve(strict=False)
        except Exception:
            return False, "RESOLVE_ERROR"
            
        try:
            if is_sensitive_path(str(path)) or is_sensitive_path(str(resolved)):
                return False, "SENSITIVE_PATH_DENIED"
                
            text = str(resolved) + ("/" if resolved.is_dir() else "")
            if any(text.startswith(prefix) for prefix in BLOCKED_PREFIXES):
                return False, "PSEUDO_FS_DENIED"
        except Exception:
            return False, "EVALUATION_ERROR"

        return True, "ALLOW_READ"

    @staticmethod
    def check_write(path: str | Path) -> Tuple[bool, str]:
        ok, reason, p = PathGuard._validate_basic(path)
        if not ok:
            return False, reason
            
        try:
            resolved = p.resolve(strict=False)
        except Exception:
            return False, "RESOLVE_ERROR"
            
        try:
            if is_sensitive_path(str(path)) or is_sensitive_path(str(resolved)):
                return False, "SENSITIVE_PATH_DENIED"
                
            text = str(resolved) + ("/" if resolved.is_dir() else "")
            if any(text.startswith(prefix) for prefix in BLOCKED_PREFIXES):
                return False, "PSEUDO_FS_DENIED"

            req_norm = Path(os.path.abspath(p))
            req_tier2 = _is_tier2(req_norm)
            res_tier2 = _is_tier2(resolved)
            
            # Reject symlink escapes
            if not req_tier2 and res_tier2:
                return False, "SYMLINK_ESCAPE_DENIED"
                
            if res_tier2:
                return False, "TIER2_WRITE_DENIED"
        except Exception:
            return False, "POLICY_EVALUATION_ERROR"
            
        return True, "ALLOW_WRITE"
