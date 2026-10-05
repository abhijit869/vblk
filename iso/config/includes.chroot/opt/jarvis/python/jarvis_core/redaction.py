"""Secret redaction helpers for tool output."""

from __future__ import annotations

import re
from typing import Any


SECRET_NAME = r"[\w.-]*(?:api[_-]?key|access[_-]?key|token|passw(?:or)?d|secret|credential)[\w.-]*"

SECRET_NAME_RE = re.compile(rf"(?i)^{SECRET_NAME}$")

SECRET_PATTERNS = [
    # NAME=value, NAME: value, "NAME": "value", NAME='value'
    re.compile(rf"(?i)({SECRET_NAME})([\"']?\s*[:=]\s*[\"']?)([^\s\"',;}}\]]+)"),
    # Authorization: Bearer <token>
    re.compile(r"(?i)(bearer)(\s+)([a-z0-9._~+/=\-]+)"),
    # PEM private keys
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
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
            if isinstance(key, str) and SECRET_NAME_RE.match(key) and isinstance(item, str) and item:
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
    if match.lastindex == 3:
        return f"{match.group(1)}{match.group(2)}{REDACTED}"
    return REDACTED
