from __future__ import annotations

import hashlib
import json
import re
from typing import Any

_SAFE_KEY_CHARS = re.compile(r"[^a-zA-Z0-9:_-]+")


def _normalize_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _normalize_value(inner_value)
            for key, inner_value in sorted(value.items(), key=lambda item: str(item[0]))
        }
    return str(value)


def make_cache_key(*parts: Any, **params: Any) -> str:
    """Create deterministic cache keys with collision-resistant suffix."""
    normalized_parts = [_normalize_value(part) for part in parts]
    normalized_params = {
        str(key): _normalize_value(value)
        for key, value in sorted(params.items(), key=lambda item: item[0])
    }
    payload = json.dumps(
        {"parts": normalized_parts, "params": normalized_params},
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    raw_prefix = ":".join(str(part) for part in normalized_parts if part is not None)
    safe_prefix = _SAFE_KEY_CHARS.sub("_", raw_prefix).strip("_")
    safe_prefix = safe_prefix or "cache"
    return f"{safe_prefix}:{digest}"
