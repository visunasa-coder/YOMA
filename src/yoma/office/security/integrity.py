"""Integrity verification for YOMA files and configuration."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path


@dataclass(frozen=True)
class IntegrityResult:
    verified: bool
    reason: str
    expected_hash: str | None = None
    actual_hash: str | None = None
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "verified": self.verified,
            "reason": self.reason,
            "expected_hash": self.expected_hash,
            "actual_hash": self.actual_hash,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class IntegrityVerifier:
    @staticmethod
    def sha256_file(path: str | Path) -> str:
        target = Path(path)

        if not target.is_file():
            raise FileNotFoundError(str(target))

        digest = hashlib.sha256()

        with target.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)

        return digest.hexdigest()

    def verify_file(
        self,
        path: str | Path,
        expected_hash: str,
    ) -> IntegrityResult:

        expected = expected_hash.strip().lower()

        if len(expected) != 64:
            return IntegrityResult(
                False,
                "invalid SHA-256 baseline",
            )

        actual = self.sha256_file(path)

        if actual != expected:
            return IntegrityResult(
                False,
                "file integrity mismatch",
                expected,
                actual,
            )

        return IntegrityResult(
            True,
            "file integrity verified",
            expected,
            actual,
        )
