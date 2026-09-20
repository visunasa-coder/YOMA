from __future__ import annotations

from datetime import datetime, timezone

from yoma.office.operations import OperationalEvent, OperationalSignal


def high_workload_rule(
    events: list[OperationalEvent],
) -> list[OperationalSignal]:
    """
    Detect an explicitly reported high-workload event.

    This rule does not infer workload from surveillance data.
    It only consumes normalized events that explicitly identify
    a high-workload condition.
    """

    signals: list[OperationalSignal] = []

    for event in events:
        if event.event_type != "workload.high":
            continue

        signals.append(
            OperationalSignal(
                signal_id=f"SIG-{event.event_id}",
                signal_type="workload.high",
                detected_at=datetime.now(timezone.utc),
                organization_id=event.organization_id,
                user_id=event.user_id,
                system_id=event.system_id,
                score=float(event.data.get("score", 1.0)),
                severity=event.severity,
                evidence_event_ids=(event.event_id,),
                data=dict(event.data),
            )
        )

    return signals
