from __future__ import annotations

import sqlite3
from pathlib import Path

from yoma.office.identity import SystemIdentity, UserIdentity


class OrganizationStatePersistence:
    """Persistent normalized organization snapshot for YOMA."""

    def __init__(self, db_path: str | Path) -> None:
        self._memory_connection: sqlite3.Connection | None = None

        if str(db_path) == ":memory:":
            self.db_path = Path(":memory:")
            self._memory_connection = sqlite3.connect(":memory:")
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        if self._memory_connection is not None:
            return self._memory_connection

        return sqlite3.connect(self.db_path)

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS yoma_organization_users (
                    user_id TEXT PRIMARY KEY,
                    name TEXT,
                    username TEXT,
                    email TEXT,
                    department TEXT,
                    role TEXT,
                    system_id TEXT,
                    active INTEGER NOT NULL DEFAULT 1
                        CHECK (active IN (0, 1))
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS yoma_organization_systems (
                    system_id TEXT PRIMARY KEY,
                    name TEXT,
                    system_number TEXT,
                    active INTEGER NOT NULL DEFAULT 1
                        CHECK (active IN (0, 1))
                )
                """
            )

    def save_users(self, users: list[UserIdentity]) -> None:
        if not isinstance(users, list):
            raise TypeError("Users must be a list")

        with self._connect() as conn:
            conn.execute(
                "DELETE FROM yoma_organization_users"
            )

            for user in users:
                conn.execute(
                    """
                    INSERT INTO yoma_organization_users (
                        user_id,
                        name,
                        username,
                        email,
                        department,
                        role,
                        system_id,
                        active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user.user_id,
                        user.name,
                        user.username,
                        user.email,
                        user.department,
                        user.role,
                        user.system_id,
                        int(user.active),
                    ),
                )

    def save_systems(
        self,
        systems: list[SystemIdentity],
    ) -> None:
        if not isinstance(systems, list):
            raise TypeError("Systems must be a list")

        with self._connect() as conn:
            conn.execute(
                "DELETE FROM yoma_organization_systems"
            )

            for system in systems:
                conn.execute(
                    """
                    INSERT INTO yoma_organization_systems (
                        system_id,
                        name,
                        system_number,
                        active
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        system.system_id,
                        system.name,
                        system.system_number,
                        int(system.active),
                    ),
                )

    def users(self) -> list[UserIdentity]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    user_id,
                    name,
                    username,
                    email,
                    department,
                    role,
                    system_id,
                    active
                FROM yoma_organization_users
                ORDER BY user_id ASC
                """
            ).fetchall()

        return [
            UserIdentity(
                user_id=row[0],
                name=row[1],
                username=row[2],
                email=row[3],
                department=row[4],
                role=row[5],
                system_id=row[6],
                active=bool(row[7]),
            )
            for row in rows
        ]

    def systems(self) -> list[SystemIdentity]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    system_id,
                    name,
                    system_number,
                    active
                FROM yoma_organization_systems
                ORDER BY system_id ASC
                """
            ).fetchall()

        return [
            SystemIdentity(
                system_id=row[0],
                name=row[1],
                system_number=row[2],
                active=bool(row[3]),
            )
            for row in rows
        ]