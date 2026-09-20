from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True)
class OperationalEvent:
    """
    Provider-neutral event representing something that happened
    inside or around an organization.

    YOMA does not require the originating system to use this model.
    Adapters normalize external events into this contract.
    """

    event_id: str
    event_type: str
    occurred_at: datetime

    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    system_id: Optional[str] = None

    source: Optional[str] = None
    location_id: Optional[str] = None

    severity: str = "info"
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def is_user_event(self) -> bool:
        return self.user_id is not None

    @property
    def is_system_event(self) -> bool:
        return self.system_id is not None


@dataclass(frozen=True)
class OperationalAction:
    """
    Normalized action that YOMA may recommend or execute.

    Execution remains subject to the relevant authorization,
    policy and approval requirements.
    """

    action_id: str
    action_type: str

    target_user_id: Optional[str] = None
    target_system_id: Optional[str] = None

    source: Optional[str] = None
    reason: Optional[str] = None

    requires_approval: bool = True
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OperationalSignal:
    """
    Higher-level interpretation derived from one or more events.
    """

    signal_id: str
    signal_type: str
    detected_at: datetime

    organization_id: Optional[str] = None
    user_id: Optional[str] = None
    system_id: Optional[str] = None

    score: float = 0.0
    severity: str = "info"

    evidence_event_ids: tuple[str, ...] = ()
    data: dict[str, Any] = field(default_factory=dict)
