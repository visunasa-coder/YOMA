from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Tuple

from yoma.office.action_planning import ActionPlan


@dataclass(frozen=True)
class PolicyConstraint:
    constraint_id: str
    constraint_type: str
    description: str
    allowed: bool = True
    action_types: Tuple[str, ...] = ()
    priorities: Tuple[str, ...] = ()
    user_ids: Tuple[str, ...] = ()
    system_ids: Tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.constraint_id.startswith("POL-"):
            raise ValueError("constraint_id must start with POL-")
        if not self.constraint_type:
            raise ValueError("constraint_type must not be empty")
        if not self.description:
            raise ValueError("description must not be empty")


@dataclass(frozen=True)
class PolicyCheckResult:
    check_id: str
    plan_id: str
    decision_id: str
    status: str
    passed_constraint_ids: Tuple[str, ...] = ()
    failed_constraint_ids: Tuple[str, ...] = ()
    reasons: Tuple[str, ...] = ()
    requires_human_approval: bool = True
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.check_id.startswith("PCHECK-"):
            raise ValueError("check_id must start with PCHECK-")
        if not self.plan_id.startswith("APLAN-"):
            raise ValueError("plan_id must start with APLAN-")
        if not self.decision_id.startswith("DINT-"):
            raise ValueError("decision_id must start with DINT-")

        if self.status not in {"allowed", "restricted", "blocked"}:
            raise ValueError("invalid policy status")

        if not self.requires_human_approval:
            raise ValueError("policy checks require human approval")

    @property
    def allowed(self) -> bool:
        return self.status == "allowed"

    @property
    def blocked(self) -> bool:
        return self.status == "blocked"

    @property
    def restricted(self) -> bool:
        return self.status == "restricted"

    @property
    def passed_count(self) -> int:
        return len(self.passed_constraint_ids)

    @property
    def failed_count(self) -> int:
        return len(self.failed_constraint_ids)


class PolicyConstraintEngine:
    """
    Evaluates an ActionPlan against explicit organizational
    policy constraints.

    This engine does not execute, enforce, or modify actions.
    """

    def __init__(
        self,
        constraints: Tuple[PolicyConstraint, ...] | list[PolicyConstraint] = (),
    ) -> None:
        self._constraints = tuple(constraints)

    @property
    def constraints(self) -> Tuple[PolicyConstraint, ...]:
        return self._constraints

    def evaluate(self, plan: ActionPlan) -> PolicyCheckResult:
        if not isinstance(plan, ActionPlan):
            raise TypeError("plan must be an ActionPlan")

        passed = []
        failed = []
        reasons = []

        for constraint in self._constraints:
            matches = self._matches(plan, constraint)

            if not matches:
                passed.append(constraint.constraint_id)
                continue

            if constraint.allowed:
                passed.append(constraint.constraint_id)
            else:
                failed.append(constraint.constraint_id)
                reasons.append(
                    f"{constraint.constraint_id}: {constraint.description}"
                )

        if failed:
            status = "blocked"
        else:
            status = "allowed"

        return PolicyCheckResult(
            check_id=f"PCHECK-{plan.plan_id}",
            plan_id=plan.plan_id,
            decision_id=plan.decision_id,
            status=status,
            passed_constraint_ids=tuple(sorted(passed)),
            failed_constraint_ids=tuple(sorted(failed)),
            reasons=tuple(reasons),
            requires_human_approval=True,
            data={
                "constraint_count": len(self._constraints),
                "plan_priority": plan.priority,
            },
        )

    def evaluate_many(
        self,
        plans: Tuple[ActionPlan, ...] | list[ActionPlan],
    ) -> Tuple[PolicyCheckResult, ...]:
        return tuple(self.evaluate(plan) for plan in plans)

    def _matches(
        self,
        plan: ActionPlan,
        constraint: PolicyConstraint,
    ) -> bool:
        if constraint.action_types:
            plan_types = {
                step.action_type
                for step in plan.steps
            }

            if not plan_types.intersection(constraint.action_types):
                return False

        if constraint.priorities:
            if plan.priority not in constraint.priorities:
                return False

        if constraint.user_ids:
            if not set(plan.affected_user_ids).intersection(
                constraint.user_ids
            ):
                return False

        if constraint.system_ids:
            if not set(plan.affected_system_ids).intersection(
                constraint.system_ids
            ):
                return False

        return bool(
            constraint.action_types
            or constraint.priorities
            or constraint.user_ids
            or constraint.system_ids
        )
