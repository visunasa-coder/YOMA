from __future__ import annotations

from typing import Any

from yoma.office.actions import ActionRequest, ActionResult, ControlledActionGateway
from yoma.office.governance.persistent import PersistentAuditLog
from yoma.office.governance.policy import PolicyEngine


class PersistentGovernedActionExecutor:
    """
    Production-oriented governed executor.

    Uses YOMA's existing SQLite audit infrastructure while keeping
    policy evaluation and action execution behind their existing
    boundaries.
    """

    def __init__(
        self,
        gateway: ControlledActionGateway,
        connection: Any,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        self.gateway = gateway
        self.connection = connection
        self.policy_engine = policy_engine or PolicyEngine()
        self.audit = PersistentAuditLog(connection)

    def execute(self, request: ActionRequest) -> ActionResult:
        policy = self.policy_engine.evaluate(request)

        if not policy.allowed:
            self.audit.record(
                event_type="action.denied",
                actor=request.requested_by,
                request_id=request.request_id,
                action_type=request.action.action_type,
                status="denied",
                reason=policy.reason,
            )

            return ActionResult(
                request_id=request.request_id,
                status="denied",
                message=policy.reason,
                executed=False,
            )

        self.audit.record(
            event_type="action.authorized",
            actor=request.requested_by,
            request_id=request.request_id,
            action_type=request.action.action_type,
            status="authorized",
        )

        try:
            result = self.gateway.execute(request)
        except Exception as exc:
            self.audit.record(
                event_type="action.failed",
                actor=request.requested_by,
                request_id=request.request_id,
                action_type=request.action.action_type,
                status="failed",
                reason="executor_error",
                metadata={
                    "error_type": type(exc).__name__,
                },
            )
            raise

        self.audit.record(
            event_type=(
                "action.executed"
                if result.executed
                else "action.failed"
            ),
            actor=request.requested_by,
            request_id=request.request_id,
            action_type=request.action.action_type,
            status=result.status,
            reason=result.message,
        )

        return result
