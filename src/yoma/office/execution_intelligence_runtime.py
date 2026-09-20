from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Mapping

from yoma.office.execution_observation import (
    ExecutionResultObservation,
    ExecutionResultObservationEngine,
)
from yoma.office.execution_reconciliation import (
    ExecutionOutcomeReconciliation,
    ExecutionOutcomeReconciliationEngine,
)
from yoma.office.execution_reliability import (
    ExecutionReliabilityIntelligence,
    ExecutionReliabilityIntelligenceEngine,
)
from yoma.office.action_planning import ActionPlan
from yoma.office.action_approval import ActionApprovalWorkflow
from yoma.office.execution_policy import ExecutionPolicyResult
from yoma.office.execution_audit import ExecutionAuditTrace


@dataclass(frozen=True)
class ExecutionIntelligenceResult:
    observations: tuple[ExecutionResultObservation, ...] = ()
    reconciliations: tuple[ExecutionOutcomeReconciliation, ...] = ()
    reliability: tuple[ExecutionReliabilityIntelligence, ...] = ()

    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        if not self.requires_human_approval:
            raise ValueError("execution intelligence requires human approval")
        if self.executable:
            raise ValueError("execution intelligence is not executable")

    @property
    def observation_count(self) -> int:
        return len(self.observations)

    @property
    def reconciliation_count(self) -> int:
        return len(self.reconciliations)

    @property
    def reliability_count(self) -> int:
        return len(self.reliability)

    @property
    def requires_review(self) -> bool:
        return any(item.requires_review for item in self.reliability)

    @property
    def action_types(self) -> tuple[str, ...]:
        values = {
            reconciliation.action_type
            for reconciliation in self.reconciliations
            if reconciliation.action_type
        }
        return tuple(sorted(values))


class ExecutionIntelligenceRuntime:
    """
    Unified execution intelligence runtime.

    Ownership boundaries:
      M32.6 -> execution result observation
      M32.7 -> outcome reconciliation
      M32.8 -> reliability intelligence

    This runtime composes those layers and does not duplicate their logic.
    It never executes an action.
    """

    def __init__(
        self,
        observation_engine: ExecutionResultObservationEngine | None = None,
        reconciliation_engine: ExecutionOutcomeReconciliationEngine | None = None,
        reliability_engine: ExecutionReliabilityIntelligenceEngine | None = None,
    ) -> None:
        self.observation_engine = (
            observation_engine or ExecutionResultObservationEngine()
        )
        self.reconciliation_engine = (
            reconciliation_engine or ExecutionOutcomeReconciliationEngine()
        )
        self.reliability_engine = (
            reliability_engine or ExecutionReliabilityIntelligenceEngine()
        )

        self._results: list[ExecutionIntelligenceResult] = []

    @property
    def results(self) -> tuple[ExecutionIntelligenceResult, ...]:
        return tuple(self._results)

    @property
    def latest(self) -> ExecutionIntelligenceResult | None:
        if not self._results:
            return None
        return self._results[-1]

    def analyze(
        self,
        workflow: ActionApprovalWorkflow,
        plan: ActionPlan,
        policy_result: ExecutionPolicyResult,
        audit_trace: ExecutionAuditTrace,
        observed_at: datetime,
        *,
        event_ids: Iterable[str] = (),
        evidence: Mapping[str, Any] | None = None,
        expected_event_count: int = 0,
        expected_success: bool | None = True,
        action_type: str | None = None,
    ) -> ExecutionIntelligenceResult:
        """
        Run the complete M32.6 -> M32.7 -> M32.8 intelligence chain.

        The observation engine owns execution-result observation.
        The reconciliation engine owns expected-vs-observed reconciliation.
        The reliability engine owns reliability analysis.
        """

        observation = self.observation_engine.observe(
            workflow=workflow,
            plan=plan,
            policy_result=policy_result,
            audit_trace=audit_trace,
            observed_at=observed_at,
            event_ids=tuple(event_ids),
            evidence=evidence,
        )

        reconciliation = self.reconciliation_engine.reconcile(
            workflow=workflow,
            plan=plan,
            audit_trace=audit_trace,
            observation=observation,
            expected_event_count=expected_event_count,
            expected_success=expected_success,
            evidence=evidence,
        )

        reliability = self.reliability_engine.analyze(
            (reconciliation,),
            action_type=action_type or reconciliation.action_type,
        )

        result = ExecutionIntelligenceResult(
            observations=(observation,),
            reconciliations=(reconciliation,),
            reliability=(reliability,),
        )

        self._results.append(result)
        return result

    def analyze_observation(
        self,
        observation: ExecutionResultObservation,
        workflow: ActionApprovalWorkflow,
        plan: ActionPlan,
        audit_trace: ExecutionAuditTrace,
        *,
        expected_event_count: int = 0,
        expected_success: bool | None = True,
        evidence: Mapping[str, Any] | None = None,
        action_type: str | None = None,
    ) -> ExecutionIntelligenceResult:
        """
        Continue the intelligence chain from an existing M32.6 observation.
        """

        reconciliation = self.reconciliation_engine.reconcile(
            workflow=workflow,
            plan=plan,
            audit_trace=audit_trace,
            observation=observation,
            expected_event_count=expected_event_count,
            expected_success=expected_success,
            evidence=evidence,
        )

        reliability = self.reliability_engine.analyze(
            (reconciliation,),
            action_type=action_type or reconciliation.action_type,
        )

        result = ExecutionIntelligenceResult(
            observations=(observation,),
            reconciliations=(reconciliation,),
            reliability=(reliability,),
        )

        self._results.append(result)
        return result

    def analyze_reconciliations(
        self,
        reconciliations: Iterable[ExecutionOutcomeReconciliation],
        *,
        action_type: str | None = None,
    ) -> ExecutionIntelligenceResult:
        """
        Analyze already-reconciled execution outcomes through M32.8.
        """

        reconciliation_tuple = tuple(reconciliations)

        reliability = self.reliability_engine.analyze(
            reconciliation_tuple,
            action_type=action_type,
        )

        result = ExecutionIntelligenceResult(
            observations=(),
            reconciliations=reconciliation_tuple,
            reliability=(reliability,),
        )

        self._results.append(result)
        return result

    def analyze_many(
        self,
        items: Iterable[
            tuple[
                ActionApprovalWorkflow,
                ActionPlan,
                ExecutionPolicyResult,
                ExecutionAuditTrace,
                datetime,
            ]
        ],
        *,
        expected_event_count: int = 0,
        expected_success: bool | None = True,
    ) -> ExecutionIntelligenceResult:
        """
        Process multiple executions and produce one aggregate reliability result.
        """

        observations: list[ExecutionResultObservation] = []
        reconciliations: list[ExecutionOutcomeReconciliation] = []

        for (
            workflow,
            plan,
            policy_result,
            audit_trace,
            observed_at,
        ) in items:
            observation = self.observation_engine.observe(
                workflow=workflow,
                plan=plan,
                policy_result=policy_result,
                audit_trace=audit_trace,
                observed_at=observed_at,
            )

            reconciliation = self.reconciliation_engine.reconcile(
                workflow=workflow,
                plan=plan,
                audit_trace=audit_trace,
                observation=observation,
                expected_event_count=expected_event_count,
                expected_success=expected_success,
            )

            observations.append(observation)
            reconciliations.append(reconciliation)

        reliability = self.reliability_engine.analyze(
            tuple(reconciliations)
        )

        result = ExecutionIntelligenceResult(
            observations=tuple(observations),
            reconciliations=tuple(reconciliations),
            reliability=(reliability,),
        )

        self._results.append(result)
        return result

    def clear(self) -> None:
        self._results.clear()
