"""Canonical JSON and content-addressed identifiers."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    """Return the project's stable JSON representation.

    Floats are accepted only if finite; Python's encoder rejects NaN/Infinity.
    UTF-8, sorted keys and compact separators make receipts replay-stable.
    """

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_uri(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical_bytes(value)
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def content_id(prefix: str, value: Any, length: int = 32) -> str:
    return f"{prefix}_{sha256_uri(value).split(':', 1)[1][:length]}"


def without_keys(value: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key not in set(keys)}


def rotating_identifier(secret: bytes, rotation_epoch: str, identifier: str) -> str:
    """Pseudonymize an identifier within a bounded local rotation epoch."""

    if len(secret) < 32:
        raise ValueError("rotation secret must be at least 32 bytes")
    normalized = identifier.strip().lower().encode("utf-8")
    digest = hmac.new(secret, rotation_epoch.encode() + b"\0" + normalized, hashlib.sha256)
    return "ephem:" + digest.hexdigest()


def keyed_content_id(prefix: str, secret: bytes, value: Any, length: int = 40) -> str:
    """Create a non-enumerable local reference for sensitive content."""

    if len(secret) < 32:
        raise ValueError("content-ID secret must be at least 32 bytes")
    digest = hmac.new(secret, canonical_bytes(value), hashlib.sha256).hexdigest()
    return f"{prefix}_{digest[:length]}"


def keyed_digest(secret: bytes, purpose: str, value: Any) -> str:
    """Return a purpose-separated, non-enumerable evidence digest."""

    if len(secret) < 32:
        raise ValueError("digest secret must be at least 32 bytes")
    subkey = hmac.new(secret, b"FLOCKOFF-DIGEST-V1\0" + purpose.encode(), hashlib.sha256).digest()
    return "hmac-sha256:" + hmac.new(subkey, canonical_bytes(value), hashlib.sha256).hexdigest()
