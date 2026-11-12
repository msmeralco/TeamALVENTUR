"""SIN hashing. The only place a raw SIN may be touched, and it is never stored."""

from __future__ import annotations

import hashlib


def sin_hash(raw_sin: str, salt: str) -> str:
    """Salted SHA-256 of a Service ID Number, as 64 hex characters."""
    return hashlib.sha256((salt + raw_sin).encode()).hexdigest()
