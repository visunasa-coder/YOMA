from datetime import datetime, timezone

from yoma.office.control_server.decision_intelligence import (
    ControlServerDecisionIntelligence,
)
from yoma.office.control_server.windows_service.runtime import (
    ControlServerRuntime,
)
from yoma.office.decision.orchestrator import DecisionContext
from yoma.office.decision_intelligence import DecisionIntelligence
from yoma.office.decision_intelligence_runtime import (
    DecisionIntelligenceRuntime,
)
from yoma.office.historical_decision_context import (
    HistoricalDecisionContext,
)
from yoma.office.predictive_decision_context import (
    PredictiveDecisionContext,
    PredictiveDecisionRecommendation,
)
from yoma.office.operations.model import OperationalSignal


NOW = datetime(
    2026,
    9,
    5,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_current():
    signal = OperationalSignal(
        signal_id="SIG-E2E-1",
        signal_type="workload.high",
        detected_at=NOW,
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        score=0.80,
        severity="high",
        evidence_event_ids=("EV-E2E-1",),
        data={},
    )

    return DecisionContext(
        signal=signal,
        recommendations=(
            {
                "type": "workload_review",
                "reason": (
                    "Operational workload signal requires human review."
                ),
                "employee_id": "U1",
                "score": 0.80,
            },
        ),
        actions=(),
        requires_human_approval=True,
    )


def make_historical():
    return HistoricalDecisionContext(
        situation_id="SIT-HIST-E2E",
        situation_type="workload.high",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        occurrence_count=3,
        historical_pattern_id="HPAT-E2E",
        baseline_daily_frequency=0.40,
        recent_daily_frequency=0.70,
        previous_daily_frequency=0.50,
        deviation_from_baseline=0.30,
        frequency_change=0.20,
        trend_ratio=1.40,
        trend_direction="rising",
        average_recurrence_interval_seconds=86400.0,
        historical_situation_ids=(
            "SIT-OLD-E2E-1",
            "SIT-OLD-E2E-2",
            "SIT-OLD-E2E-3",
        ),
        evidence=(
            "Repeated workload pressure.",
        ),
        requires_human_approval=True,
    )


def make_predictive():
    recommendation = PredictiveDecisionRecommendation(
        recommendation_id="PREC-REC-E2E",
        recommendation_type="predictive_workload_review",
        reason=(
            "Predicted workload pressure requires human review."
        ),
        priority="high",
        target_user_id="U1",
        target_system_id=None,
        evidence=(
            "Historical recurrence supports future workload risk.",
        ),
        requires_human_approval=True,
    )

    return PredictiveDecisionContext(
        context_id="PCTX-E2E",
        prediction_id="PRED-E2E",
        situation_type="workload.high",
        organization_id="ORG1",
        user_id="U1",
        system_id=None,
        created_at=NOW,
        probability=0.80,
        confidence=0.75,
        severity="high",
        forecast_start=NOW,
        forecast_end=NOW.replace(day=6),
        recommendation=recommendation,
        evidence_situation_ids=(
            "SIT-E2E-1",
            "SIT-E2E-2",
        ),
        evidence=(
            "Predicted recurrence.",
        ),
        actions=(),
        requires_human_approval=True,
    )


def test_m30_9_full_decision_intelligence_e2e():
    current = make_current()
    historical = make_historical()
    predictive = make_predictive()

    decision_runtime = DecisionIntelligenceRuntime()

    result = decision_runtime.analyze(
        current_decisions=(current,),
        historical_contexts=(historical,),
        predictive_contexts=(predictive,),
    )

    assert result.decision_count == 1
    assert result.graph_count == 1
    assert result.explanation_count == 1

    decision = result.decisions[0]

    assert isinstance(decision, DecisionIntelligence)

    assert decision.current_intelligence_available is True
    assert decision.historical_intelligence_available is True
    assert decision.predictive_intelligence_available is True

    assert decision.organization_id == "ORG1"
    assert decision.user_id == "U1"
    assert decision.situation_type == "workload.high"

    assert decision.requires_human_approval is True


def test_m30_9_fusion_preserves_all_context_layers():
    runtime = DecisionIntelligenceRuntime()

    result = runtime.analyze(
        current_decisions=(make_current(),),
        historical_contexts=(make_historical(),),
        predictive_contexts=(make_predictive(),),
    )

    decision = result.decisions[0]

    assert decision.current_decision_ids
    assert decision.historical_context_ids
    assert decision.predictive_context_ids


def test_m30_9_evidence_graph_is_connected_to_decision():
    runtime = DecisionIntelligenceRuntime()

    result = runtime.analyze(
        current_decisions=(make_current(),),
        historical_contexts=(make_historical(),),
        predictive_contexts=(make_predictive(),),
    )

    graph = result.graphs[0]
    decision = result.decisions[0]

    assert graph.decision_id == decision.decision_id
    assert graph.node(decision.decision_id) is not None
    assert graph.node_count >= 1
    assert graph.edge_count >= 1


def test_m30_9_explanation_is_connected_to_decision():
    runtime = DecisionIntelligenceRuntime()

    result = runtime.analyze(
        current_decisions=(make_current(),),
        historical_contexts=(make_historical(),),
        predictive_contexts=(make_predictive(),),
    )

    explanation = result.explanations[0]
    decision = result.decisions[0]

    assert explanation.decision_id == decision.decision_id
    assert explanation.explanation_id == (
        f"DEXP-{decision.decision_id}"
    )
    assert explanation.summary
    assert explanation.why_it_matters
    assert explanation.recommendation


def test_m30_9_priority_ranking_exists():
    runtime = DecisionIntelligenceRuntime()

    result = runtime.analyze(
        current_decisions=(make_current(),),
        historical_contexts=(make_historical(),),
        predictive_contexts=(make_predictive(),),
    )

    assert result.ranking is not None
    assert result.ranking.count == 1
    assert result.top_decision is result.ranking.top_decision
    assert result.ranking.scores


def test_m30_9_predictive_evidence_is_present():
    runtime = DecisionIntelligenceRuntime()

    result = runtime.analyze(
        current_decisions=(make_current(),),
        historical_contexts=(make_historical(),),
        predictive_contexts=(make_predictive(),),
    )

    decision = result.decisions[0]

    assert decision.evidence

    evidence_ids = {
        item.evidence_id
        for item in decision.evidence
    }

    assert evidence_ids


def test_m30_9_control_server_boundary_exposes_latest():
    decision_runtime = DecisionIntelligenceRuntime()

    decision_runtime.analyze(
        current_decisions=(make_current(),),
        historical_contexts=(make_historical(),),
        predictive_contexts=(make_predictive(),),
    )

    server = ControlServerRuntime(
        host="127.0.0.1",
        port=0,
    )

    integration = ControlServerDecisionIntelligence(
        server,
        decision_runtime,
    )

    status = integration.status()
    latest = integration.latest()

    assert status.available is True
    assert status.decision_count == 1
    assert status.explanation_count == 1

    assert latest is not None
    assert latest["decision_count"] == 1
    assert latest["graph_count"] == 1
    assert latest["explanation_count"] == 1


def test_m30_9_human_approval_is_preserved_end_to_end():
    runtime = DecisionIntelligenceRuntime()

    result = runtime.analyze(
        current_decisions=(make_current(),),
        historical_contexts=(make_historical(),),
        predictive_contexts=(make_predictive(),),
    )

    assert result.requires_human_review is True

    for decision in result.decisions:
        assert decision.requires_human_approval is True

    for explanation in result.explanations:
        assert explanation.requires_human_approval is True


def test_m30_9_no_autonomous_execution_surface():
    runtime = DecisionIntelligenceRuntime()

    public_names = {
        name
        for name in dir(runtime)
        if not name.startswith("_")
    }

    assert "execute" not in public_names
    assert "approve" not in public_names
    assert "execute_action" not in public_names


def test_m30_9_deterministic_structure():
    runtime = DecisionIntelligenceRuntime()

    first = runtime.analyze(
        current_decisions=(make_current(),),
        historical_contexts=(make_historical(),),
        predictive_contexts=(make_predictive(),),
    )

    second = runtime.analyze(
        current_decisions=(make_current(),),
        historical_contexts=(make_historical(),),
        predictive_contexts=(make_predictive(),),
    )

    assert len(first.decisions) == len(second.decisions)
    assert len(first.graphs) == len(second.graphs)
    assert len(first.explanations) == len(second.explanations)

    assert first.decisions[0].decision_id == (
        second.decisions[0].decision_id
    )

    assert first.graphs[0].decision_id == (
        second.graphs[0].decision_id
    )

    assert first.explanations[0].explanation_id == (
        second.explanations[0].explanation_id
    )
