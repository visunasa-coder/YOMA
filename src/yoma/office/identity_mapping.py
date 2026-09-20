from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4


class IdentityMapping:
    """Maps external provider identities to stable YOMA identity IDs."""

    def __init__(
        self,
        *,
        persistence: IdentityMappingPersistence | None = None,
    ) -> None:
        self.persistence = persistence
        self._external_to_internal: dict[tuple[str, str], str] = {}
        self._internal_to_external: dict[str, dict[str, str]] = {}

    def map(self, *, provider: str, external_id: str) -> str:
        provider = str(provider).strip()
        external_id = str(external_id).strip()

        if not provider:
            raise ValueError("provider is required")

        if not external_id:
            raise ValueError("external_id is required")

        key = (provider, external_id)

        existing = self._external_to_internal.get(key)

        if existing is not None:
            return existing

        if self.persistence is not None:
            existing = self.persistence.get_internal_id(
                provider=provider,
                external_id=external_id,
            )

            if existing is not None:
                self._external_to_internal[key] = existing
                self._internal_to_external[existing] = {
                    "provider": provider,
                    "external_id": external_id,
                }
                return existing

        internal_id = str(uuid4())

        self._external_to_internal[key] = internal_id
        self._internal_to_external[internal_id] = {
            "provider": provider,
            "external_id": external_id,
        }

        if self.persistence is not None:
            self.persistence.save(
                provider=provider,
                external_id=external_id,
                internal_id=internal_id,
            )

        return internal_id

    def get_internal_id(
        self,
        *,
        provider: str,
        external_id: str,
    ) -> str | None:
        provider = str(provider).strip()
        external_id = str(external_id).strip()

        if not provider:
            raise ValueError("provider is required")

        if not external_id:
            raise ValueError("external_id is required")

        key = (provider, external_id)

        existing = self._external_to_internal.get(key)

        if existing is not None:
            return existing

        if self.persistence is not None:
            existing = self.persistence.get_internal_id(
                provider=provider,
                external_id=external_id,
            )

            if existing is not None:
                self._external_to_internal[key] = existing
                self._internal_to_external[existing] = {
                    "provider": provider,
                    "external_id": external_id,
                }

            return existing

        return None

    def get_external_identity(
        self,
        internal_id: str,
    ) -> dict[str, str] | None:
        internal_id = str(internal_id).strip()

        if not internal_id:
            raise ValueError("internal_id is required")

        existing = self._internal_to_external.get(internal_id)

        if existing is not None:
            return dict(existing)

        if self.persistence is not None:
            existing = self.persistence.get_external_identity(
                internal_id
            )

            if existing is not None:
                self._internal_to_external[internal_id] = dict(existing)
                self._external_to_internal[
                    (
                        existing["provider"],
                        existing["external_id"],
                    )
                ] = internal_id

            return existing

        return None

    def count(self) -> int:
        if self.persistence is not None:
            return self.persistence.count()

        return len(self._external_to_internal)


class IdentityMappingPersistence:
    """SQLite persistence for external-to-YOMA identity mappings."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS yoma_identity_mappings (
                    provider TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    internal_id TEXT NOT NULL UNIQUE,
                    PRIMARY KEY (provider, external_id)
                )
                """
            )

    def save(
        self,
        *,
        provider: str,
        external_id: str,
        internal_id: str,
    ) -> None:
        provider = str(provider).strip()
        external_id = str(external_id).strip()
        internal_id = str(internal_id).strip()

        if not provider:
            raise ValueError("provider is required")

        if not external_id:
            raise ValueError("external_id is required")

        if not internal_id:
            raise ValueError("internal_id is required")

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO yoma_identity_mappings (
                    provider,
                    external_id,
                    internal_id
                )
                VALUES (?, ?, ?)
                ON CONFLICT(provider, external_id) DO UPDATE SET
                    internal_id = excluded.internal_id
                """,
                (provider, external_id, internal_id),
            )

    def get_internal_id(
        self,
        *,
        provider: str,
        external_id: str,
    ) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT internal_id
                FROM yoma_identity_mappings
                WHERE provider = ?
                  AND external_id = ?
                """,
                (provider, external_id),
            ).fetchone()

        return row[0] if row else None

    def get_external_identity(
        self,
        internal_id: str,
    ) -> dict[str, str] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT provider, external_id
                FROM yoma_identity_mappings
                WHERE internal_id = ?
                """,
                (internal_id,),
            ).fetchone()

        if row is None:
            return None

        return {
            "provider": row[0],
            "external_id": row[1],
        }

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM yoma_identity_mappings"
            ).fetchone()

        return int(row[0])
