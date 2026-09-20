from __future__ import annotations

from abc import abstractmethod
from typing import Any

from ..base import YomaAdapter


class SecurityAdapter(YomaAdapter):
    category = "security"

    @abstractmethod
    def events(self, **filters: Any) -> list[dict[str, Any]]:
        """
        Return authorized security events from existing systems.

        This contract intentionally does not require continuous
        employee surveillance.
        """
        raise NotImplementedError
