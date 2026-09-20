"""Local encrypted credential vault for YOMA M13.4."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any


class CredentialVaultError(RuntimeError):
    """Base error for credential-vault failures."""


class CredentialNotFound(CredentialVaultError):
    """Raised when a credential does not exist."""


class CredentialVault:
    """Small local encrypted credential store.

    The vault stores only encrypted credential blobs on disk.
    It deliberately has no logging and never returns persisted
    plaintext storage.
    """

    VERSION = 1
    _NONCE_BYTES = 16
    _TAG_BYTES = 32

    def __init__(self, path: str | Path, master_key: bytes) -> None:
        if not master_key:
            raise CredentialVaultError("master key is unavailable")

        if len(master_key) < 32:
            raise CredentialVaultError("master key must be at least 32 bytes")

        self._path = Path(path)
        self._master_key = bytes(master_key)

    def _derive_key(self, nonce: bytes) -> bytes:
        return hashlib.sha256(self._master_key + nonce).digest()

    def _crypt(self, data: bytes, key: bytes) -> bytes:
        output = bytearray()

        counter = 0
        while len(output) < len(data):
            block = hashlib.sha256(
                key + counter.to_bytes(8, "big")
            ).digest()
            output.extend(block)
            counter += 1

        return bytes(
            value ^ stream
            for value, stream in zip(data, output[: len(data)])
        )

    def _read(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}

        try:
            raw = self._path.read_bytes()
            document = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise CredentialVaultError("credential vault is unreadable") from exc

        if not isinstance(document, dict):
            raise CredentialVaultError("credential vault has invalid format")

        return document

    def _write(self, document: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

        temporary = self._path.with_suffix(
            self._path.suffix + ".tmp"
        )

        temporary.write_text(
            json.dumps(document, separators=(",", ":")),
            encoding="utf-8",
        )

        os.replace(temporary, self._path)

    def store(
        self,
        credential_id: str,
        value: dict[str, Any],
    ) -> None:
        if not credential_id:
            raise CredentialVaultError("credential ID is required")

        if not isinstance(value, dict):
            raise CredentialVaultError("credential value must be an object")

        plaintext = json.dumps(
            value,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

        nonce = os.urandom(self._NONCE_BYTES)
        key = self._derive_key(nonce)
        ciphertext = self._crypt(plaintext, key)
        tag = hmac.new(
            key,
            nonce + ciphertext,
            hashlib.sha256,
        ).digest()

        document = self._read()
        credentials = document.setdefault("credentials", {})

        credentials[credential_id] = {
            "version": self.VERSION,
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
            "tag": base64.b64encode(tag).decode("ascii"),
        }

        self._write(document)

    def retrieve(self, credential_id: str) -> dict[str, Any]:
        document = self._read()
        credentials = document.get("credentials", {})

        entry = credentials.get(credential_id)
        if entry is None:
            raise CredentialNotFound(credential_id)

        try:
            nonce = base64.b64decode(entry["nonce"])
            ciphertext = base64.b64decode(entry["ciphertext"])
            tag = base64.b64decode(entry["tag"])
        except Exception as exc:
            raise CredentialVaultError("credential entry is malformed") from exc

        key = self._derive_key(nonce)
        expected_tag = hmac.new(
            key,
            nonce + ciphertext,
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(tag, expected_tag):
            raise CredentialVaultError("credential integrity check failed")

        try:
            plaintext = self._crypt(ciphertext, key)
            value = json.loads(plaintext.decode("utf-8"))
        except Exception as exc:
            raise CredentialVaultError("credential decryption failed") from exc

        if not isinstance(value, dict):
            raise CredentialVaultError("credential payload is invalid")

        return value

    def exists(self, credential_id: str) -> bool:
        document = self._read()
        return credential_id in document.get("credentials", {})

    def delete(self, credential_id: str) -> None:
        document = self._read()
        credentials = document.get("credentials", {})

        if credential_id not in credentials:
            raise CredentialNotFound(credential_id)

        del credentials[credential_id]
        self._write(document)
