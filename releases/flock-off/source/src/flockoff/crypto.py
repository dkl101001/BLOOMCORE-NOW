"""Authenticated encryption for restricted route records."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .canonical import canonical_bytes


@dataclass(frozen=True)
class EncryptedRecord:
    key_id: str
    nonce: bytes
    ciphertext: bytes


class FieldCipher:
    """AES-256-GCM envelope; callers must obtain keys from a platform keystore."""

    def __init__(self, key: bytes):
        if len(key) != 32:
            raise ValueError("AES-256-GCM key must be exactly 32 bytes")
        self._key = key
        self.key_id = hashlib.sha256(key).hexdigest()[:16]

    @classmethod
    def from_base64(cls, encoded: str) -> "FieldCipher":
        return cls(base64.b64decode(encoded, validate=True))

    @staticmethod
    def generate_key_base64() -> str:
        return base64.b64encode(AESGCM.generate_key(bit_length=256)).decode("ascii")

    def encrypt(self, value: Any, associated_data: str) -> EncryptedRecord:
        nonce = os.urandom(12)
        ciphertext = AESGCM(self._key).encrypt(
            nonce, canonical_bytes(value), associated_data.encode("utf-8")
        )
        return EncryptedRecord(self.key_id, nonce, ciphertext)

    def keyed_digest(self, value: Any) -> str:
        digest_key = hmac.new(self._key, b"FLOCKOFF-VAULT-DIGEST-V1", hashlib.sha256).digest()
        return "hmac-sha256:" + hmac.new(digest_key, canonical_bytes(value), hashlib.sha256).hexdigest()

    def decrypt(self, record: EncryptedRecord, associated_data: str) -> bytes:
        if record.key_id != self.key_id:
            raise ValueError("wrong route-encryption key")
        return AESGCM(self._key).decrypt(
            record.nonce, record.ciphertext, associated_data.encode("utf-8")
        )
