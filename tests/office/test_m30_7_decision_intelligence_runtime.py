from datetime import datetime, timezone

from yoma.office.decision_intelligence import (
    DecisionIntelligenceEvidence,
)
from yoma.office.decision_intelligence_runtime import (
    DecisionIntelligenceResult,
    DecisionIntelligenceRuntime,
)


def test_runtime_initial_state():
    runtime = DecisionIntelligenceRuntime()

    assert runtime.last_result is None
    assert runtime.decision_count == 0


def test_runtime_analyze_empty():
    runtime = DecisionIntelligenceRuntime()

    result = runtime.analyze()

    assert isinstance(result, DecisionIntelligenceResult)
    assert result.decisions == ()
    assert result.graphs == ()
    assert result.explanations == ()
    assert result.decision_count == 0


def test_runtime_stores_last_result():
    runtime = DecisionIntelligenceRuntime()

    result = runtime.analyze()

    assert runtime.last_result is result


def test_runtime_clear_last_result():
    runtime = DecisionIntelligenceRuntime()

    runtime.analyze()
    runtime.clear_last_result()

    assert runtime.last_result is None


def test_result_properties_empty():
    result = DecisionIntelligenceResult()

    assert result.decision_count == 0
    assert result.graph_count == 0
    assert result.explanation_count == 0
    assert result.top_decision is None
    assert result.requires_human_review is False
    assert result.intelligence_available is False


def test_runtime_accepts_prebuilt_components():
    from yoma.office.current_historical_decision_fusion import (
        CurrentHistoricalDecisionFusion,
    )
    from yoma.office.predictive_decision_fusion import (
        PredictiveDecisionFusion,
    )
    from yoma.office.decision_priority import DecisionPriorityRanker
    from yoma.office.decision_evidence_graph import (
        DecisionEvidenceGraphBuilder,
    )
    from yoma.office.decision_explanation import (
        DecisionExplanationEngine,
    )

    runtime = DecisionIntelligenceRuntime(
        fusion=PredictiveDecisionFusion(),
        ranker=DecisionPriorityRanker(),
        graph_builder=DecisionEvidenceGraphBuilder(),
        explanation_engine=DecisionExplanationEngine(),
    )

    assert runtime.last_result is None


def test_runtime_analyze_one_exists():
    runtime = DecisionIntelligenceRuntime()

    assert callable(runtime.analyze_one)


def test_runtime_repeated_empty_analysis_is_deterministic():
    runtime = DecisionIntelligenceRuntime()

    first = runtime.analyze()
    second = runtime.analyze()

    assert first == second


def test_result_human_review_defaults_safe():
    result = DecisionIntelligenceResult()

    assert result.requires_human_review is False


def test_runtime_does_not_execute_actions():
    runtime = DecisionIntelligenceRuntime()

    result = runtime.analyze()

    assert result.decisions == ()
    assert result.graphs == ()
    assert result.explanations == ()


def test_runtime_result_graph_and_explanation_counts_align():
    runtime = DecisionIntelligenceRuntime()

    result = runtime.analyze()

    assert result.graph_count == result.decision_count
    assert result.explanation_count == result.decision_count
