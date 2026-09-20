from __future__ import annotations

from abc import abstractmethod
from typing import Any

from ..base import YomaAdapter


class EmailAdapter(YomaAdapter):
    category = "email"

    @abstractmethod
    def list_messages(self, **filters: Any) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def send_message(self, message: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
