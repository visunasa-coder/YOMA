from datetime import datetime, timezone
import sqlite3

from yoma.office.adapters.base import YomaAdapter
from yoma.office.actions import ActionRequest, ControlledActionGateway
from yoma.office.decision import DecisionOrchestrator
from yoma.office.governance import (
    PersistentGovernedActionExecutor,
    PolicyEngine,
)
from yoma.office.intelligence import OperationalIntelligenceEngine
from yoma.office.intelligence.rules import high_workload_rule
from yoma.office.operations import OperationalAction, OperationalEvent
from yoma.office.runtime import YomaEmbeddedRuntime


class EndToEndAdapter(YomaAdapter):
    name = "e2e_adapter"
    category = "test"

    def health(self):
        return {"status": "healthy"}

    def capabilities(self):
        return ["workload_events"]

    def connect(self, config):
        pass

    def disconnect(self):
        pass

    def collect_events(self):
        return [
            OperationalEvent(
                event_id="E2E-EVENT-001",
                event_type="workload.high",
                occurred_at=datetime.now(timezone.utc),
                organization_id="ORG001",
                user_id="USER001",
                source=self.name,
                severity="warning",
                data={
                    "workload_score": 92,
                    "overtime_hours": 4.5,
                },
            )
        ]


def create_audit_db():
    db = sqlite3.connect(":memory:")

    db.execute(
        """
        CREATE TABLE audit_events (
            id INTEGER PRIMARY KEY,
            event_type TEXT NOT NULL,
            username TEXT,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    return db


def test_complete_yoma_embedded_pipeline():
    """
    M15 end-to-end validation.

    Adapter
        -> Runtime
        -> Event Bus
        -> Intelligence
        -> Decision
        -> Governance
        -> Action Gateway
        -> Persistent Audit
    """

    db = create_audit_db()

    # ---------------------------------------------------------
    # 1. Build the intelligence layer
    # ---------------------------------------------------------

    intelligence = OperationalIntelligenceEngine()

    intelligence.register_rule(
        "high_workload",
        high_workload_rule,
    )

    # ---------------------------------------------------------
    # 2. Build the decision layer
    # ---------------------------------------------------------

    decisions = DecisionOrchestrator()

    # Use the existing workload decision handler.
    from yoma.office.decision.rules import workload_decision

    decisions.register_handler(
        "workload.high",
        workload_decision,
    )

    # ---------------------------------------------------------
    # 3. Build the controlled action gateway
    # ---------------------------------------------------------

    gateway = ControlledActionGateway()

    executed_actions = []

    def execute_workload_review(action):
        executed_actions.append(action)
        return {
            "reviewed": True,
            "employee": action.target_user_id,
        }

    gateway.register_executor(
        "workload.review",
        execute_workload_review,
    )

    # ---------------------------------------------------------
    # 4. Build persistent governance
    # ---------------------------------------------------------

    policy_engine = PolicyEngine()

    governed_executor = PersistentGovernedActionExecutor(
        gateway,
        db,
        policy_engine,
    )

    # ---------------------------------------------------------
    # 5. Build embedded runtime
    # ---------------------------------------------------------

    runtime = YomaEmbeddedRuntime(
        intelligence=intelligence,
        decisions=decisions,
        governed_executor=governed_executor,
    )

    runtime.register_adapter(EndToEndAdapter())

    # ---------------------------------------------------------
    # 6. Start the embedded system
    # ---------------------------------------------------------

    runtime.start()

    assert runtime.running is True
    assert runtime.status().adapter_count == 1

    # ---------------------------------------------------------
    # 7. Collect events from adapter
    # ---------------------------------------------------------

    events = runtime.collect_events()

    assert len(events) == 1
    assert events[0].event_type == "workload.high"
    assert events[0].user_id == "USER001"

    # ---------------------------------------------------------
    # 8. Intelligence detects operational signal
    # ---------------------------------------------------------

    signals = runtime.analyze(events)

    assert len(signals) == 1
    assert signals[0].signal_type == "workload.high"
    assert signals[0].user_id == "USER001"

    # ---------------------------------------------------------
    # 9. Decision orchestration
    # ---------------------------------------------------------

    contexts = runtime.decide(signals)

    assert len(contexts) == 1
    assert len(contexts[0].actions) == 1

    action = contexts[0].actions[0]

    assert action.action_type == "workload.review"
    assert action.target_user_id == "USER001"
    assert action.requires_approval is True

    # ---------------------------------------------------------
    # 10. Convert decision into action request
    # ---------------------------------------------------------

    request = ActionRequest(
        request_id="E2E-REQUEST-001",
        action=action,
        requested_by="admin",
        requested_at=datetime.now(timezone.utc),
        approval_token="E2E_APPROVED",
    )

    # ---------------------------------------------------------
    # 11. Governed execution
    # ---------------------------------------------------------

    result = governed_executor.execute(request)

    assert result.executed is True
    assert result.status == "executed"
    assert executed_actions

    # ---------------------------------------------------------
    # 12. Persistent audit validation
    # ---------------------------------------------------------

    rows = db.execute(
        """
        SELECT event_type
        FROM audit_events
        ORDER BY id
        """
    ).fetchall()

    audit_events = [row[0] for row in rows]

    assert "action.authorized" in audit_events
    assert "action.executed" in audit_events

    # ---------------------------------------------------------
    # 13. Stop the embedded system
    # ---------------------------------------------------------

    runtime.stop()

    assert runtime.running is False


def test_e2e_policy_can_block_action():
    db = create_audit_db()

    gateway = ControlledActionGateway()

    executed = []

    gateway.register_executor(
        "workload.review",
        lambda action: executed.append(action),
    )

    policies = PolicyEngine()

    from yoma.office.governance.policy import PolicyDecision

    policies.register(
        "block_test_action",
        lambda request: PolicyDecision(
            allowed=False,
            reason="enterprise_policy_block",
        ),
    )

    governed = PersistentGovernedActionExecutor(
        gateway,
        db,
        policies,
    )

    action = OperationalAction(
        action_id="BLOCK-001",
        action_type="workload.review",
        target_user_id="USER001",
        requires_approval=False,
    )

    request = ActionRequest(
        request_id="BLOCK-REQUEST-001",
        action=action,
        requested_by="admin",
        requested_at=datetime.now(timezone.utc),
    )

    result = governed.execute(request)

    assert result.executed is False
    assert result.status == "denied"
    assert executed == []

    row = db.execute(
        """
        SELECT event_type
        FROM audit_events
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()

    assert row[0] == "action.denied"


def test_e2e_runtime_rejects_operations_after_shutdown():
    runtime = YomaEmbeddedRuntime()

    runtime.start()
    runtime.stop()

    assert runtime.running is False

    event = OperationalEvent(
        event_id="SHUTDOWN-001",
        event_type="test.event",
        occurred_at=datetime.now(timezone.utc),
    )

    try:
        runtime.publish(event)
        assert False, "Runtime accepted an event after shutdown"
    except RuntimeError as exc:
        assert "not running" in str(exc)
