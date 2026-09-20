from __future__ import annotations

from yoma.office.actions import ActionRequest, ActionResult, ControlledActionGateway
from yoma.office.governance.policy import AuditLog, PolicyEngine


class GovernedActionExecutor:
    """
    Combines policy evaluation, controlled execution and audit logging.

    The action gateway remains the final execution boundary.
    """

    def __init__(
        self,
        gateway: ControlledActionGateway,
        policy_engine: PolicyEngine | None = None,
        audit_log: AuditLog | None = None,
    ) -> None:
        self.gateway = gateway
        self.policy_engine = policy_engine or PolicyEngine()
        self.audit_log = audit_log or AuditLog()

    def execute(self, request: ActionRequest) -> ActionResult:
        policy = self.policy_engine.evaluate(request)

        if not policy.allowed:
            self.audit_log.record(
                audit_id=f"AUDIT-{request.request_id}",
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

        self.audit_log.record(
            audit_id=f"AUDIT-{request.request_id}-REQUEST",
            event_type="action.authorized",
            actor=request.requested_by,
            request_id=request.request_id,
            action_type=request.action.action_type,
            status="authorized",
        )

        result = self.gateway.execute(request)

        self.audit_log.record(
            audit_id=f"AUDIT-{request.request_id}-RESULT",
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
