"""Utility helpers for generating URL-friendly slugs."""
from __future__ import annotations

import re
import unicodedata

_INVALID_CHARS_RE = re.compile(r"[^\w\s-]", flags=re.UNICODE)
_SEPARATOR_RE = re.compile(r"[-\s_]+", flags=re.UNICODE)


def slugify(value: str, *, max_length: int = 255, default: str = "item") -> str:
    """Convert an arbitrary string into a URL-friendly slug."""
    if not value:
        return default

    normalized = unicodedata.normalize("NFKD", value)
    cleaned = _INVALID_CHARS_RE.sub("", normalized)
    lowered = cleaned.strip().lower()
    slug = _SEPARATOR_RE.sub("-", lowered).strip("-")

    if not slug:
        slug = default

    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
        if not slug:
            slug = default

    return slug

