from __future__ import annotations

from abc import abstractmethod
from typing import Any

from ..base import YomaAdapter


class AttendanceAdapter(YomaAdapter):
    category = "attendance"

    @abstractmethod
    def fetch_events(
        self,
        *,
        employee_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return normalized attendance events.

        The implementation may connect to an existing biometric,
        punch, access-control, or attendance system.
        """
        raise NotImplementedError
