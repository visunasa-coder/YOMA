from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Tuple


VALID_ORCHESTRATION_HEALTH = {
    "healthy",
    "attention",
    "blocked",
    "failed",
    "unknown",
}


@dataclass(frozen=True)
class OrchestrationHealth:
    health_id: str
    orchestration_id: str
    execution_plan_id: str
    status: str
    action_count: int = 0
    completed_action_count: int = 0
    blocked_action_count: int = 0
    pending_action_count: int = 0
    participating_system_count: int = 0
    blocked_system_count: int = 0
    unresolved_system_count: int = 0
    dependency_issue_count: int = 0
    approval_pending_count: int = 0
    rollback_required: bool = False
    risk_score: float = 0.0
    requires_human_approval: bool = True
    executable: bool = False
    reasons: Tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.health_id.startswith("OHEALTH-"):
            raise ValueError("health_id must start with OHEALTH-")

        if not self.orchestration_id:
            raise ValueError("orchestration_id must be non-empty")

        if not self.execution_plan_id:
            raise ValueError("execution_plan_id must be non-empty")

        if self.status not in VALID_ORCHESTRATION_HEALTH:
            raise ValueError(
                f"invalid orchestration health: {self.status}"
            )

        numeric_fields = (
            self.action_count,
            self.completed_action_count,
            self.blocked_action_count,
            self.pending_action_count,
            self.participating_system_count,
            self.blocked_system_count,
            self.unresolved_system_count,
            self.dependency_issue_count,
            self.approval_pending_count,
        )

        if any(value < 0 for value in numeric_fields):
            raise ValueError("monitoring counts cannot be negative")

        if not 0.0 <= self.risk_score <= 1.0:
            raise ValueError("risk_score must be between 0 and 1")

        if not self.requires_human_approval:
            raise ValueError(
                "orchestration intelligence requires human approval"
            )

        if self.executable:
            raise ValueError(
                "orchestration intelligence is non-executable"
            )

    @property
    def requires_review(self) -> bool:
        return (
            self.status != "healthy"
            or self.blocked_action_count > 0
            or self.blocked_system_count > 0
            or self.unresolved_system_count > 0
            or self.dependency_issue_count > 0
            or self.approval_pending_count > 0
            or self.rollback_required
            or self.risk_score >= 0.65
        )


@dataclass(frozen=True)
class OrchestrationProgress:
    progress_id: str
    orchestration_id: str
    execution_plan_id: str
    total_actions: int
    completed_actions: int
    pending_actions: int
    blocked_actions: int
    progress_ratio: float
    completed_action_ids: Tuple[str, ...] = ()
    pending_action_ids: Tuple[str, ...] = ()
    blocked_action_ids: Tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        if not self.progress_id.startswith("OPROG-"):
            raise ValueError("progress_id must start with OPROG-")

        if self.total_actions < 0:
            raise ValueError("total_actions cannot be negative")

        if self.completed_actions < 0:
            raise ValueError("completed_actions cannot be negative")

        if self.pending_actions < 0:
            raise ValueError("pending_actions cannot be negative")

        if self.blocked_actions < 0:
            raise ValueError("blocked_actions cannot be negative")

        if (
            self.completed_actions
            + self.pending_actions
            + self.blocked_actions
            != self.total_actions
        ):
            raise ValueError(
                "action progress counts must equal total_actions"
            )

        if not 0.0 <= self.progress_ratio <= 1.0:
            raise ValueError(
                "progress_ratio must be between 0 and 1"
            )

        if not self.requires_human_approval:
            raise ValueError(
                "orchestration progress requires human approval"
            )

        if self.executable:
            raise ValueError(
                "orchestration progress is non-executable"
            )


@dataclass(frozen=True)
class OrchestrationMonitoringSignal:
    signal_id: str
    orchestration_id: str
    execution_plan_id: str
    signal_type: str
    severity: str
    score: float
    reason: str
    evidence: Tuple[str, ...] = ()
    requires_human_approval: bool = True
    executable: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.signal_id.startswith("OMON-"):
            raise ValueError("signal_id must start with OMON-")

        if not self.orchestration_id:
            raise ValueError("orchestration_id must be non-empty")

        if not self.execution_plan_id:
            raise ValueError("execution_plan_id must be non-empty")

        if not self.signal_type:
            raise ValueError("signal_type must be non-empty")

        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0 and 1")

        if not self.requires_human_approval:
            raise ValueError(
                "monitoring signals require human approval"
            )

        if self.executable:
            raise ValueError(
                "monitoring signals are non-executable"
            )


@dataclass(frozen=True)
class OrchestrationIntelligence:
    intelligence_id: str
    orchestration_id: str
    execution_plan_id: str
    health: OrchestrationHealth
    progress: OrchestrationProgress
    monitoring_signals: Tuple[
        OrchestrationMonitoringSignal, ...
    ] = ()
    coordination_id: Optional[str] = None
    schedule_id: Optional[str] = None
    transaction_id: Optional[str] = None
    rollback_plan_id: Optional[str] = None
    approval_pending_count: int = 0
    requires_human_approval: bool = True
    executable: bool = False
    recommendation: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.intelligence_id.startswith("OINT-"):
            raise ValueError("intelligence_id must start with OINT-")

        if (
            self.health.orchestration_id
            != self.orchestration_id
        ):
            raise ValueError(
                "health must belong to the orchestration"
            )

        if (
            self.progress.orchestration_id
            != self.orchestration_id
        ):
            raise ValueError(
                "progress must belong to the orchestration"
            )

        if not self.requires_human_approval:
            raise ValueError(
                "orchestration intelligence requires human approval"
            )

        if self.executable:
            raise ValueError(
                "orchestration intelligence is non-executable"
            )

    @property
    def signal_count(self) -> int:
        return len(self.monitoring_signals)

    @property
    def requires_review(self) -> bool:
        return (
            self.health.requires_review
            or bool(self.monitoring_signals)
        )


class OrchestrationIntelligenceEngine:
    """
    M33.8 Orchestration Intelligence & Monitoring.

    This engine observes orchestration state from M33.3-M33.7
    and produces deterministic health, progress and monitoring
    intelligence.

    It does not execute, approve, modify, schedule or cancel actions.
    """

    def __init__(self) -> None:
        self._cache: dict[str, OrchestrationIntelligence] = {}

    def _validate(
        self,
        execution_plan: Any,
        execution_order: Any,
        transaction: Any,
        coordination: Any,
        schedule: Any,
        approval_items: Tuple[Any, ...],
    ) -> None:
        if execution_plan.execution_plan_id != execution_order.execution_plan_id:
            raise ValueError("execution order does not match plan")

        if transaction.execution_plan_id != execution_plan.execution_plan_id:
            raise ValueError("transaction does not match plan")

        if coordination.execution_plan_id != execution_plan.execution_plan_id:
            raise ValueError("coordination does not match plan")

        if schedule.execution_plan_id != execution_plan.execution_plan_id:
            raise ValueError("schedule does not match plan")

        for item in approval_items:
            if item.execution_plan_id != execution_plan.execution_plan_id:
                raise ValueError(
                    "approval queue item does not match plan"
                )

    def _progress(
        self,
        execution_plan: Any,
        execution_order: Any,
        approval_items: Tuple[Any, ...],
    ) -> OrchestrationProgress:
        actions = tuple(execution_plan.actions)

        blocked = set(execution_order.blocked_action_ids)

        approved_action_ids: set[str] = set()

        for item in approval_items:
            if item.status == "approved":
                approved_action_ids.update(
                    action.action_id
                    for action in actions
                )

        pending = {
            action.action_id
            for action in actions
            if action.action_id not in blocked
            and action.action_id not in approved_action_ids
        }

        completed: set[str] = set()

        # M33.8 is intentionally observational. An approved action is
        # not considered executed merely because it was approved.
        # Therefore completion remains zero until actual execution
        # evidence is supplied by a later execution-observation layer.
        completed -= blocked

        total = len(actions)

        return OrchestrationProgress(
            progress_id=f"OPROG-{execution_plan.execution_plan_id}",
            orchestration_id=execution_plan.orchestration_id,
            execution_plan_id=execution_plan.execution_plan_id,
            total_actions=total,
            completed_actions=len(completed),
            pending_actions=len(pending),
            blocked_actions=len(blocked),
            progress_ratio=(
                round(len(completed) / total, 6)
                if total
                else 0.0
            ),
            completed_action_ids=tuple(sorted(completed)),
            pending_action_ids=tuple(sorted(pending)),
            blocked_action_ids=tuple(sorted(blocked)),
        )

    def _signals(
        self,
        execution_plan: Any,
        execution_order: Any,
        coordination: Any,
        schedule: Any,
        transaction: Any,
        approval_items: Tuple[Any, ...],
        progress: OrchestrationProgress,
    ) -> Tuple[OrchestrationMonitoringSignal, ...]:
        signals: list[OrchestrationMonitoringSignal] = []

        if execution_order.missing_dependency_ids:
            signals.append(
                OrchestrationMonitoringSignal(
                    signal_id=(
                        f"OMON-{execution_plan.execution_plan_id}-"
                        "missing-dependency"
                    ),
                    orchestration_id=execution_plan.orchestration_id,
                    execution_plan_id=execution_plan.execution_plan_id,
                    signal_type="dependency.missing",
                    severity="high",
                    score=0.85,
                    reason="Execution plan contains missing dependencies.",
                    evidence=tuple(
                        execution_order.missing_dependency_ids
                    ),
                )
            )

        if execution_order.blocked_action_ids:
            signals.append(
                OrchestrationMonitoringSignal(
                    signal_id=(
                        f"OMON-{execution_plan.execution_plan_id}-"
                        "blocked-action"
                    ),
                    orchestration_id=execution_plan.orchestration_id,
                    execution_plan_id=execution_plan.execution_plan_id,
                    signal_type="orchestration.blocked",
                    severity="high",
                    score=0.80,
                    reason="One or more actions are blocked.",
                    evidence=tuple(
                        execution_order.blocked_action_ids
                    ),
                )
            )

        if coordination.unresolved_system_ids:
            signals.append(
                OrchestrationMonitoringSignal(
                    signal_id=(
                        f"OMON-{execution_plan.execution_plan_id}-"
                        "unresolved-system"
                    ),
                    orchestration_id=execution_plan.orchestration_id,
                    execution_plan_id=execution_plan.execution_plan_id,
                    signal_type="system.unresolved",
                    severity="high",
                    score=0.82,
                    reason="One or more participating systems are unresolved.",
                    evidence=tuple(
                        coordination.unresolved_system_ids
                    ),
                )
            )

        if coordination.coordination_order is not None:
            if coordination.coordination_order.circular_dependency:
                signals.append(
                    OrchestrationMonitoringSignal(
                        signal_id=(
                            f"OMON-{execution_plan.execution_plan_id}-"
                            "system-cycle"
                        ),
                        orchestration_id=execution_plan.orchestration_id,
                        execution_plan_id=execution_plan.execution_plan_id,
                        signal_type="system.circular_dependency",
                        severity="critical",
                        score=0.95,
                        reason=(
                            "Cross-system coordination contains "
                            "a circular dependency."
                        ),
                    )
                )

        pending_approvals = sum(
            1
            for item in approval_items
            if item.status == "pending"
        )

        if pending_approvals:
            signals.append(
                OrchestrationMonitoringSignal(
                    signal_id=(
                        f"OMON-{execution_plan.execution_plan_id}-"
                        "approval-pending"
                    ),
                    orchestration_id=execution_plan.orchestration_id,
                    execution_plan_id=execution_plan.execution_plan_id,
                    signal_type="approval.pending",
                    severity="warning",
                    score=min(
                        1.0,
                        round(
                            0.40 + (pending_approvals * 0.05),
                            6,
                        ),
                    ),
                    reason=(
                        "Human approval is pending for "
                        "the orchestration."
                    ),
                    evidence=tuple(
                        item.queue_item_id
                        for item in approval_items
                        if item.status == "pending"
                    ),
                )
            )

        rollback_required = getattr(
            transaction,
            "rollback_required",
            False,
        )

        if hasattr(transaction, "rollback_plan"):
            rollback_required = (
                getattr(
                    transaction.rollback_plan,
                    "rollback_required",
                    rollback_required,
                )
            )

        if rollback_required:
            signals.append(
                OrchestrationMonitoringSignal(
                    signal_id=(
                        f"OMON-{execution_plan.execution_plan_id}-"
                        "rollback-required"
                    ),
                    orchestration_id=execution_plan.orchestration_id,
                    execution_plan_id=execution_plan.execution_plan_id,
                    signal_type="transaction.rollback_required",
                    severity="critical",
                    score=0.90,
                    reason=(
                        "Transaction intelligence indicates "
                        "rollback is required."
                    ),
                )
            )

        if schedule.status == "cancelled":
            signals.append(
                OrchestrationMonitoringSignal(
                    signal_id=(
                        f"OMON-{execution_plan.execution_plan_id}-"
                        "schedule-cancelled"
                    ),
                    orchestration_id=execution_plan.orchestration_id,
                    execution_plan_id=execution_plan.execution_plan_id,
                    signal_type="schedule.cancelled",
                    severity="warning",
                    score=0.65,
                    reason="The execution schedule is cancelled.",
                )
            )

        return tuple(
            sorted(
                signals,
                key=lambda signal: (
                    signal.severity,
                    signal.signal_id,
                ),
            )
        )

    def _health(
        self,
        execution_plan: Any,
        execution_order: Any,
        coordination: Any,
        transaction: Any,
        approval_items: Tuple[Any, ...],
        progress: OrchestrationProgress,
        signals: Tuple[OrchestrationMonitoringSignal, ...],
    ) -> OrchestrationHealth:
        pending_approvals = sum(
            1
            for item in approval_items
            if item.status == "pending"
        )

        unresolved_systems = len(
            coordination.unresolved_system_ids
        )

        # ExecutionOrder does not expose circular_dependency.
        # Circular dependency is represented by the dependency engine
        # raising during ordering, while DependencyExecutionAnalysis
        # exposes the explicit circular_dependency field.
        dependency_issues = len(
            execution_order.missing_dependency_ids
        )

        blocked_systems = len(
            coordination.coordination_order.blocked_system_ids
            if coordination.coordination_order is not None
            else ()
        )

        rollback_required = getattr(
            transaction,
            "rollback_required",
            False,
        )

        if hasattr(transaction, "rollback_plan"):
            rollback_required = (
                getattr(
                    transaction.rollback_plan,
                    "rollback_required",
                    rollback_required,
                )
            )

        if rollback_required:
            status = "failed"
        elif (
            False
            or execution_order.missing_dependency_ids
            or progress.blocked_actions
        ):
            status = "blocked"
        elif (
            unresolved_systems
            or blocked_systems
            or pending_approvals
            or signals
        ):
            status = "attention"
        else:
            status = "healthy"

        risk_components = []

        if execution_order.missing_dependency_ids:
            risk_components.append(0.85)

        if False:
            risk_components.append(0.95)

        if progress.blocked_actions:
            risk_components.append(0.80)

        if unresolved_systems:
            risk_components.append(0.82)

        if blocked_systems:
            risk_components.append(0.78)

        if pending_approvals:
            risk_components.append(
                min(1.0, 0.40 + pending_approvals * 0.05)
            )

        if rollback_required:
            risk_components.append(0.90)

        risk_score = (
            round(max(risk_components), 6)
            if risk_components
            else 0.0
        )

        reasons = tuple(
            signal.reason
            for signal in signals
        )

        return OrchestrationHealth(
            health_id=f"OHEALTH-{execution_plan.execution_plan_id}",
            orchestration_id=execution_plan.orchestration_id,
            execution_plan_id=execution_plan.execution_plan_id,
            status=status,
            action_count=progress.total_actions,
            completed_action_count=progress.completed_actions,
            blocked_action_count=progress.blocked_actions,
            pending_action_count=progress.pending_actions,
            participating_system_count=(
                len(coordination.participating_system_ids)
            ),
            blocked_system_count=blocked_systems,
            unresolved_system_count=unresolved_systems,
            dependency_issue_count=dependency_issues,
            approval_pending_count=pending_approvals,
            rollback_required=rollback_required,
            risk_score=risk_score,
            reasons=reasons,
        )

    def analyze(
        self,
        execution_plan: Any,
        execution_order: Any,
        transaction: Any,
        coordination: Any,
        schedule: Any,
        approval_items: Tuple[Any, ...] = (),
    ) -> OrchestrationIntelligence:
        self._validate(
            execution_plan,
            execution_order,
            transaction,
            coordination,
            schedule,
            tuple(approval_items),
        )

        intelligence_id = (
            f"OINT-{execution_plan.execution_plan_id}"
        )

        if intelligence_id in self._cache:
            return self._cache[intelligence_id]

        approval_items = tuple(approval_items)

        progress = self._progress(
            execution_plan,
            execution_order,
            approval_items,
        )

        signals = self._signals(
            execution_plan,
            execution_order,
            coordination,
            schedule,
            transaction,
            approval_items,
            progress,
        )

        health = self._health(
            execution_plan,
            execution_order,
            coordination,
            transaction,
            approval_items,
            progress,
            signals,
        )

        if health.status == "healthy":
            recommendation = (
                "Orchestration is structurally healthy; "
                "continue human-governed processing."
            )
        elif health.status == "blocked":
            recommendation = (
                "Resolve dependency or blocking conditions "
                "before proceeding."
            )
        elif health.status == "failed":
            recommendation = (
                "Review transaction failure and rollback "
                "requirements before proceeding."
            )
        else:
            recommendation = (
                "Human review is recommended before proceeding."
            )

        result = OrchestrationIntelligence(
            intelligence_id=intelligence_id,
            orchestration_id=execution_plan.orchestration_id,
            execution_plan_id=execution_plan.execution_plan_id,
            health=health,
            progress=progress,
            monitoring_signals=signals,
            coordination_id=coordination.coordination_id,
            schedule_id=schedule.schedule_id,
            transaction_id=getattr(
                transaction,
                "transaction_id",
                None,
            ),
            rollback_plan_id=(
                getattr(
                    transaction,
                    "rollback_plan_id",
                    None,
                )
                or getattr(
                    getattr(transaction, "rollback_plan", None),
                    "rollback_plan_id",
                    None,
                )
            ),
            approval_pending_count=health.approval_pending_count,
            recommendation=recommendation,
        )

        self._cache[intelligence_id] = result
        return result

    def analyze_many(
        self,
        inputs: Tuple[Tuple[Any, Any, Any, Any, Any, Tuple[Any, ...]], ...],
    ) -> Tuple[OrchestrationIntelligence, ...]:
        return tuple(
            self.analyze(
                execution_plan,
                execution_order,
                transaction,
                coordination,
                schedule,
                approval_items,
            )
            for (
                execution_plan,
                execution_order,
                transaction,
                coordination,
                schedule,
                approval_items,
            ) in inputs
        )

    def get(self, intelligence_id: str) -> OrchestrationIntelligence:
        if not intelligence_id.startswith("OINT-"):
            raise ValueError(
                "intelligence_id must start with OINT-"
            )

        try:
            return self._cache[intelligence_id]
        except KeyError as exc:
            raise KeyError(
                f"unknown orchestration intelligence: {intelligence_id}"
            ) from exc

    @property
    def intelligence(self) -> Tuple[OrchestrationIntelligence, ...]:
        return tuple(
            self._cache[key]
            for key in sorted(self._cache)
        )

    def clear(self) -> None:
        self._cache.clear()
