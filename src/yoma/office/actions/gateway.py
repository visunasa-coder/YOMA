from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from yoma.office.operations import OperationalAction


@dataclass(frozen=True)
class ActionRequest:
    request_id: str
    action: OperationalAction
    requested_by: str
    requested_at: datetime
    approval_token: str | None = None


@dataclass(frozen=True)
class ActionResult:
    request_id: str
    status: str
    message: str
    executed: bool = False
    data: dict[str, Any] | None = None


class ControlledActionGateway:
    """
    Security boundary between YOMA recommendations and execution.

    Actions are never executed merely because an AI or intelligence
    component generated them.

    An action must:
      1. be registered,
      2. be explicitly requested,
      3. satisfy authorization,
      4. satisfy approval requirements,
      5. pass policy,
      6. have an executor.
    """

    def __init__(self) -> None:
        self._executors: dict[str, Callable[[OperationalAction], Any]] = {}
        self._policies: list[
            Callable[[ActionRequest], tuple[bool, str]]
        ] = []

    def register_executor(
        self,
        action_type: str,
        executor: Callable[[OperationalAction], Any],
    ) -> None:
        if not action_type or not action_type.strip():
            raise ValueError("action_type is required")

        if action_type in self._executors:
            raise ValueError(
                f"Executor already registered: {action_type}"
            )

        self._executors[action_type] = executor

    def add_policy(
        self,
        policy: Callable[[ActionRequest], tuple[bool, str]],
    ) -> None:
        self._policies.append(policy)

    def list_actions(self) -> list[str]:
        return list(self._executors)

    def authorize(
        self,
        request: ActionRequest,
    ) -> tuple[bool, str]:
        action = request.action

        if action.action_type not in self._executors:
            return False, "action_not_supported"

        if action.requires_approval and not request.approval_token:
            return False, "approval_required"

        for policy in self._policies:
            allowed, reason = policy(request)

            if not allowed:
                return False, reason

        return True, "authorized"

    def execute(
        self,
        request: ActionRequest,
    ) -> ActionResult:
        allowed, reason = self.authorize(request)

        if not allowed:
            return ActionResult(
                request_id=request.request_id,
                status="denied",
                message=reason,
                executed=False,
            )

        executor = self._executors[request.action.action_type]

        result = executor(request.action)

        data = result if isinstance(result, dict) else None

        return ActionResult(
            request_id=request.request_id,
            status="executed",
            message="Action executed successfully",
            executed=True,
            data=data,
        )

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)
