from datetime import datetime, timezone

import pytest

from yoma.office.decision.orchestrator import DecisionContext
from yoma.office.decision_intelligence_runtime import (
    DecisionIntelligenceRuntime,
)
from yoma.office.intelligence.operational_unified_control_bridge import (
    OperationalUnifiedControlBridge,
)
from yoma.office.intelligence.operational_unified_runtime import (
    OperationalUnifiedResult,
)
from yoma.office.operations.model import OperationalSignal
from yoma.office.unified_control_runtime import UnifiedControlRuntime


NOW = datetime(
    2026,
    9,
    6,
    12,
    0,
    tzinfo=timezone.utc,
)


def _operational_result() -> OperationalUnifiedResult:
    signal = OperationalSignal(
        signal_id="SIG-M34-3",
        signal_type="workload.high",
        detected_at=NOW,
        organization_id="ORG-TEST",
        user_id="USER-TEST",
        system_id="SYSTEM-TEST",
        score=0.80,
        severity="high",
        evidence_event_ids=("EV-M34-3",),
        data={},
    )

    decision = DecisionContext(
        signal=signal,
        recommendations=(
            {
                "type": "workload_review",
                "reason": (
                    "Operational workload signal "
                    "requires human review."
                ),
                "employee_id": "USER-TEST",
                "score": 0.80,
            },
        ),
        actions=(),
        requires_human_approval=True,
    )

    return OperationalUnifiedResult(
        events=(),
        signals=(signal,),
        situations=(),
        contexts=(),
        patterns=(),
        decisions=(decision,),
    )


def test_bridge_constructs_with_existing_runtimes() -> None:
    bridge = OperationalUnifiedControlBridge(
        decision_runtime=DecisionIntelligenceRuntime(),
        unified_control_runtime=UnifiedControlRuntime(),
    )

    assert bridge.executable is False
    assert bridge.requires_human_approval is True
    assert bridge.last_result is None


def test_bridge_requires_operational_unified_result() -> None:
    bridge = OperationalUnifiedControlBridge()

    with pytest.raises(TypeError):
        bridge.process(
            object(),
            scheduled_at=NOW,
            created_at=NOW,
        )


def test_bridge_requires_timezone_aware_timestamps() -> None:
    bridge = OperationalUnifiedControlBridge()
    operational = _operational_result()
    naive = datetime(2026, 9, 6, 12, 0)

    with pytest.raises(ValueError):
        bridge.process(
            operational,
            scheduled_at=naive,
            created_at=NOW,
        )

    with pytest.raises(ValueError):
        bridge.process(
            operational,
            scheduled_at=NOW,
            created_at=naive,
        )


def test_bridge_converts_operational_decisions_to_decision_intelligence() -> None:
    bridge = OperationalUnifiedControlBridge()

    result = bridge.process(
        _operational_result(),
        scheduled_at=NOW,
        created_at=NOW,
    )

    assert result.decision_intelligence.decision_count == 1

    decision = result.decision_intelligence.decisions[0]

    assert decision.decision_id.startswith("DINT-")
    assert decision.requires_human_approval is True


def test_bridge_reaches_unified_control_runtime() -> None:
    bridge = OperationalUnifiedControlBridge()

    result = bridge.process(
        _operational_result(),
        scheduled_at=NOW,
        created_at=NOW,
    )

    assert len(result.unified_control) == 1

    control = result.unified_control[0]

    assert control.decision_id.startswith("DINT-")
    assert control.requires_human_approval is True
    assert control.executable is False
    assert control.approval_pending is True


def test_bridge_preserves_human_approval_boundary() -> None:
    bridge = OperationalUnifiedControlBridge()

    result = bridge.process(
        _operational_result(),
        scheduled_at=NOW,
        created_at=NOW,
    )

    assert result.requires_human_approval is True
    assert result.executable is False

    for control in result.unified_control:
        assert control.requires_human_approval is True
        assert control.executable is False


def test_bridge_stores_last_result() -> None:
    bridge = OperationalUnifiedControlBridge()

    result = bridge.process(
        _operational_result(),
        scheduled_at=NOW,
        created_at=NOW,
    )

    assert bridge.last_result is result
