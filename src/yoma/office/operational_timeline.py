from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from yoma.office.operational_event_persistence import OperationalEventPersistence
from yoma.office.operational_signal_persistence import OperationalSignalPersistence
from yoma.office.operational_situation_persistence import OperationalSituationPersistence
from yoma.office.operations import OperationalEvent, OperationalSignal, OperationalSituation


@dataclass(frozen=True)
class OperationalTimelineEntry:
    """Unified historical representation of one operational artifact."""

    entry_type: str
    entry_id: str
    occurred_at: datetime
    organization_id: str | None = None
    user_id: str | None = None
    system_id: str | None = None
    severity: str = "info"
    payload: Any = None


class OperationalTimeline:
    """
    Unified read-only timeline over persisted events, signals and situations.

    This class intentionally does not introduce another persistence layer.
    It composes the existing durable stores and reconstructs a deterministic
    chronological operational history.
    """

    _TYPE_ORDER = {
        "event": 0,
        "signal": 1,
        "situation": 2,
    }

    def __init__(
        self,
        event_persistence: OperationalEventPersistence,
        signal_persistence: OperationalSignalPersistence,
        situation_persistence: OperationalSituationPersistence,
    ) -> None:
        if not isinstance(event_persistence, OperationalEventPersistence):
            raise TypeError(
                "event_persistence must be an OperationalEventPersistence"
            )

        if not isinstance(signal_persistence, OperationalSignalPersistence):
            raise TypeError(
                "signal_persistence must be an OperationalSignalPersistence"
            )

        if not isinstance(
            situation_persistence,
            OperationalSituationPersistence,
        ):
            raise TypeError(
                "situation_persistence must be an OperationalSituationPersistence"
            )

        self.event_persistence = event_persistence
        self.signal_persistence = signal_persistence
        self.situation_persistence = situation_persistence

    @staticmethod
    def _event_entry(event: OperationalEvent) -> OperationalTimelineEntry:
        return OperationalTimelineEntry(
            entry_type="event",
            entry_id=event.event_id,
            occurred_at=event.occurred_at,
            organization_id=event.organization_id,
            user_id=event.user_id,
            system_id=event.system_id,
            severity=event.severity,
            payload=event,
        )

    @staticmethod
    def _signal_entry(signal: OperationalSignal) -> OperationalTimelineEntry:
        return OperationalTimelineEntry(
            entry_type="signal",
            entry_id=signal.signal_id,
            occurred_at=signal.detected_at,
            organization_id=signal.organization_id,
            user_id=signal.user_id,
            system_id=signal.system_id,
            severity=signal.severity,
            payload=signal,
        )

    @staticmethod
    def _situation_entry(
        situation: OperationalSituation,
    ) -> OperationalTimelineEntry:
        return OperationalTimelineEntry(
            entry_type="situation",
            entry_id=situation.situation_id,
            occurred_at=situation.detected_at,
            organization_id=situation.organization_id,
            user_id=situation.user_id,
            system_id=situation.system_id,
            severity=situation.severity,
            payload=situation,
        )

    @classmethod
    def _sort_key(cls, entry: OperationalTimelineEntry) -> tuple:
        return (
            entry.occurred_at,
            cls._TYPE_ORDER.get(entry.entry_type, 99),
            entry.entry_id,
        )

    def load_all(self) -> list[OperationalTimelineEntry]:
        """Return every persisted operational artifact chronologically."""
        entries: list[OperationalTimelineEntry] = []

        entries.extend(
            self._event_entry(event)
            for event in self.event_persistence.load_all()
        )
        entries.extend(
            self._signal_entry(signal)
            for signal in self.signal_persistence.load_all()
        )
        entries.extend(
            self._situation_entry(situation)
            for situation in self.situation_persistence.load_all()
        )

        entries.sort(key=self._sort_key)
        return entries

    def count(self) -> int:
        """Return the total number of timeline entries."""
        return (
            self.event_persistence.count()
            + self.signal_persistence.count()
            + self.situation_persistence.count()
        )

    def by_type(self, entry_type: str) -> list[OperationalTimelineEntry]:
        """Return timeline entries of one artifact type."""
        entry_type = str(entry_type).strip().lower()

        if entry_type not in self._TYPE_ORDER:
            raise ValueError(
                "entry_type must be one of: event, signal, situation"
            )

        return [
            entry
            for entry in self.load_all()
            if entry.entry_type == entry_type
        ]

    def by_organization(
        self,
        organization_id: str,
    ) -> list[OperationalTimelineEntry]:
        organization_id = str(organization_id).strip()

        if not organization_id:
            raise ValueError("organization_id is required")

        return [
            entry
            for entry in self.load_all()
            if entry.organization_id == organization_id
        ]

    def by_user(self, user_id: str) -> list[OperationalTimelineEntry]:
        user_id = str(user_id).strip()

        if not user_id:
            raise ValueError("user_id is required")

        return [
            entry
            for entry in self.load_all()
            if entry.user_id == user_id
        ]

    def by_system(self, system_id: str) -> list[OperationalTimelineEntry]:
        system_id = str(system_id).strip()

        if not system_id:
            raise ValueError("system_id is required")

        return [
            entry
            for entry in self.load_all()
            if entry.system_id == system_id
        ]

    def between(
        self,
        start: datetime,
        end: datetime,
    ) -> list[OperationalTimelineEntry]:
        if not isinstance(start, datetime):
            raise TypeError("start must be a datetime")

        if not isinstance(end, datetime):
            raise TypeError("end must be a datetime")

        if start > end:
            raise ValueError("start must not be after end")

        return [
            entry
            for entry in self.load_all()
            if start <= entry.occurred_at <= end
        ]

    def related_to_event(
        self,
        event_id: str,
    ) -> list[OperationalTimelineEntry]:
        """Return an event and historical artifacts referencing it."""
        event_id = str(event_id).strip()

        if not event_id:
            raise ValueError("event_id is required")

        entries: list[OperationalTimelineEntry] = []

        event = self.event_persistence.get(event_id)
        if event is not None:
            entries.append(self._event_entry(event))

        for signal in self.signal_persistence.by_evidence_event(event_id):
            entries.append(self._signal_entry(signal))

        for situation in self.situation_persistence.by_evidence_event(
            event_id
        ):
            entries.append(self._situation_entry(situation))

        entries.sort(key=self._sort_key)
        return entries

    def related_to_signal(
        self,
        signal_id: str,
    ) -> list[OperationalTimelineEntry]:
        """Return a signal and situations derived from that signal."""
        signal_id = str(signal_id).strip()

        if not signal_id:
            raise ValueError("signal_id is required")

        entries: list[OperationalTimelineEntry] = []

        signal = self.signal_persistence.get(signal_id)
        if signal is not None:
            entries.append(self._signal_entry(signal))

        for situation in self.situation_persistence.by_signal(signal_id):
            entries.append(self._situation_entry(situation))

        entries.sort(key=self._sort_key)
        return entries

    def related_to_situation(
        self,
        situation_id: str,
    ) -> list[OperationalTimelineEntry]:
        """Return a situation plus its persisted signals and evidence events."""
        situation_id = str(situation_id).strip()

        if not situation_id:
            raise ValueError("situation_id is required")

        situation = self.situation_persistence.get(situation_id)
        if situation is None:
            return []

        entries: list[OperationalTimelineEntry] = [
            self._situation_entry(situation)
        ]

        for signal_id in situation.signal_ids:
            signal = self.signal_persistence.get(signal_id)
            if signal is not None:
                entries.append(self._signal_entry(signal))

        for event_id in situation.evidence_event_ids:
            event = self.event_persistence.get(event_id)
            if event is not None:
                entries.append(self._event_entry(event))

        entries.sort(key=self._sort_key)
        return entries
