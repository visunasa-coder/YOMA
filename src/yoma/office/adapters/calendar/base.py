from __future__ import annotations

from abc import abstractmethod
from typing import Any

from ..base import YomaAdapter


class CalendarAdapter(YomaAdapter):
    category = "calendar"

    @abstractmethod
    def list_events(self, **filters: Any) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def create_event(self, event: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
