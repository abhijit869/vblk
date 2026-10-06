"""Secret redaction helpers for tool output.

Everything a tool returns may be forwarded to a cloud AI provider, stored in
memory, or written to the audit log, so all of it passes through here first.
"""

from __future__ import annotations

import re
from typing import Any

SECRET_NAME = r"[\w.-]*(?:api[_-]?key|access[_-]?key|token|passw(?:or)?d|passwd|secret|credential|private[_-]?key|cookie)[\w.-]*"

SECRET_NAME_RE = re.compile(rf"(?i)^{SECRET_NAME}$")

# Patterns with three groups keep group 1 + 2 and redact group 3.
SECRET_PATTERNS = [
    # NAME=value, NAME: value, "NAME": "value", NAME='value'
    re.compile(rf"(?i)({SECRET_NAME})([\"']?\s*[:=]\s*[\"']?)([^\s\"',;}}\]]+)"),
    # Authorization: Bearer <token> / Basic <b64>
    re.compile(r"(?i)(bearer|basic)(\s+)([a-z0-9._~+/=\-]{8,})"),
    # Credentials embedded in URLs: scheme://user:password@host
    re.compile(r"(?i)([a-z][a-z0-9+.-]*://[^/\s:@]+)(:)([^@\s/]+)(?=@)"),
    # PEM private keys / PGP private key blocks
    re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        re.DOTALL,
    ),
    re.compile(
        r"-----BEGIN PGP PRIVATE KEY BLOCK-----.*?-----END PGP PRIVATE KEY BLOCK-----",
        re.DOTALL,
    ),
    # Well-known token formats
    re.compile(
        r"\bsk-(?:proj-|ant-|live-|test-)?[A-Za-z0-9_\-]{16,}"
    ),  # OpenAI / Anthropic / Stripe
    re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}"),  # Google API key
    re.compile(r"\bya29\.[0-9A-Za-z_\-]{20,}"),  # Google OAuth token
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}"),  # GitHub
    re.compile(r"\bglpat-[A-Za-z0-9_\-]{20,}"),  # GitLab
    re.compile(r"\bxox[abposr]-[A-Za-z0-9\-]{10,}"),  # Slack
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),  # AWS access key id
    re.compile(r"\bhf_[A-Za-z0-9]{30,}"),  # Hugging Face
    re.compile(
        r"\beyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"
    ),  # JWT
    # Unix password hashes (shadow format: $id$salt$hash)
    re.compile(r"\$(?:1|2[abxy]?|5|6|y|gy|7)\$[^\s:$]{1,64}\$[^\s:]{8,}"),
]

REDACTED = "[REDACTED]"


def redact_text(value: str) -> tuple[str, bool]:
    redacted = value
    changed = False
    for pattern in SECRET_PATTERNS:
        redacted, count = pattern.subn(_replace_secret, redacted)
        changed = changed or count > 0
    return redacted, changed


def redact_data(value: Any) -> tuple[Any, bool]:
    """Recursively redact strings and secret-named keys in JSON-like data."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        changed = False
        result: dict[Any, Any] = {}
        for key, item in value.items():
            if (
                isinstance(key, str)
                and SECRET_NAME_RE.match(key)
                and isinstance(item, str)
                and item
            ):
                result[key] = REDACTED
                changed = True
                continue
            result[key], item_changed = redact_data(item)
            changed = changed or item_changed
        return result, changed
    if isinstance(value, (list, tuple)):
        changed = False
        items = []
        for item in value:
            redacted_item, item_changed = redact_data(item)
            items.append(redacted_item)
            changed = changed or item_changed
        return items, changed
    return value, False


def _replace_secret(match: re.Match[str]) -> str:
    if match.re.groups >= 3 and match.lastindex is not None and match.lastindex >= 3:
        return f"{match.group(1)}{match.group(2)}{REDACTED}"
    return REDACTED
