"""Light text normalization for complaint classification."""

from __future__ import annotations

import re

_WHITESPACE = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^a-z0-9\s]")


def normalize_text(text: str) -> str:
    """Normalize complaint text without changing meaning aggressively."""
    cleaned = str(text).lower().strip()
    cleaned = _NON_ALNUM.sub(" ", cleaned)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()
    return cleaned
