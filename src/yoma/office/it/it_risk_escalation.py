from __future__ import annotations

from dataclasses import dataclass


_VALID_RISK_LEVELS = {
    "low",
    "normal",
    "high",
    "critical",
}

_VALID_RISK_TYPES = {
    "organization",
    "project",
    "ticket",
    "incident",
    "sla",
    "deployment",
    "release",
    "workload",
    "capacity",
    "dependency",
    "bottleneck",
}


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class ITRiskSignal:
    signal_id: str
    organization_id: str
    risk_type: str
    level: str
    title: str
    description: str = ""
    source_id: str | None = None
    owner_id: str | None = None
    escalation_required: bool = False

    def __post_init__(self) -> None:
        _text(self.signal_id, "signal_id")
        _text(self.organization_id, "organization_id")
        _text(self.risk_type, "risk_type")
        _text(self.level, "level")
        _text(self.title, "title")

        if self.risk_type not in _VALID_RISK_TYPES:
            raise ValueError(f"invalid risk_type: {self.risk_type}")

        if self.level not in _VALID_RISK_LEVELS:
            raise ValueError(f"invalid level: {self.level}")

        if not isinstance(self.description, str):
            raise ValueError("description must be a string")

        if self.source_id is not None:
            _text(self.source_id, "source_id")

        if self.owner_id is not None:
            _text(self.owner_id, "owner_id")

        if not isinstance(self.escalation_required, bool):
            raise ValueError(
                "escalation_required must be boolean"
            )


@dataclass(frozen=True)
class ITRiskPortfolio:
    organization_id: str
    signals: tuple[ITRiskSignal, ...] = ()

    def __post_init__(self) -> None:
        _text(self.organization_id, "organization_id")

        if not isinstance(self.signals, tuple):
            raise ValueError("signals must be a tuple")

        signal_ids: set[str] = set()

        for signal in self.signals:
            if not isinstance(signal, ITRiskSignal):
                raise ValueError(
                    "signals must contain ITRiskSignal instances"
                )

            if signal.organization_id != self.organization_id:
                raise ValueError(
                    "signal organization_id mismatch"
                )

            if signal.signal_id in signal_ids:
                raise ValueError(
                    f"duplicate signal_id: {signal.signal_id}"
                )

            signal_ids.add(signal.signal_id)


@dataclass(frozen=True)
class ITRecommendation:
    recommendation_id: str
    signal_id: str
    organization_id: str
    priority: str
    title: str
    rationale: str
    recommended_action: str
    requires_human_approval: bool = True
    executable: bool = False

    def __post_init__(self) -> None:
        _text(self.recommendation_id, "recommendation_id")
        _text(self.signal_id, "signal_id")
        _text(self.organization_id, "organization_id")
        _text(self.priority, "priority")
        _text(self.title, "title")
        _text(self.rationale, "rationale")
        _text(self.recommended_action, "recommended_action")

        if self.priority not in _VALID_RISK_LEVELS:
            raise ValueError(
                f"invalid priority: {self.priority}"
            )

        if self.requires_human_approval is not True:
            raise ValueError(
                "recommendations must require human approval"
            )

        if self.executable is not False:
            raise ValueError(
                "recommendations must not be executable"
            )


@dataclass(frozen=True)
class ITRiskEscalationAnalysis:
    organization_id: str
    signal_count: int
    low_risk_count: int
    normal_risk_count: int
    high_risk_count: int
    critical_risk_count: int
    escalation_candidate_count: int
    ownerless_risk_count: int
    recommendation_count: int
    top_risk_signal_id: str | None
    top_risk_level: str | None
    recommendations: tuple[ITRecommendation, ...]
    issues: tuple[str, ...]
    requires_human_approval: bool = True
    executable: bool = False


@dataclass(frozen=True)
class ITRiskEscalationIntelligence:
    """
    Read-only IT risk, escalation and recommendation intelligence.

    This component converts observed risk signals into explainable
    recommendations. It does not perform escalation, reassignment,
    remediation, configuration changes, or operational execution.
    """

    def analyze(
        self,
        portfolio: ITRiskPortfolio,
    ) -> ITRiskEscalationAnalysis:
        if not isinstance(portfolio, ITRiskPortfolio):
            raise TypeError(
                "portfolio must be ITRiskPortfolio"
            )

        signals = tuple(
            sorted(
                portfolio.signals,
                key=lambda signal: signal.signal_id,
            )
        )

        low = sum(
            1 for signal in signals
            if signal.level == "low"
        )

        normal = sum(
            1 for signal in signals
            if signal.level == "normal"
        )

        high = sum(
            1 for signal in signals
            if signal.level == "high"
        )

        critical = sum(
            1 for signal in signals
            if signal.level == "critical"
        )

        escalation_candidates = sum(
            1
            for signal in signals
            if signal.escalation_required
            or signal.level in {"high", "critical"}
        )

        ownerless = sum(
            1
            for signal in signals
            if signal.owner_id is None
            and signal.level in {"high", "critical"}
        )

        top_signal = self._top_signal(signals)

        recommendations = tuple(
            self._recommendation_for_signal(signal)
            for signal in signals
            if signal.level in {"high", "critical"}
            or signal.escalation_required
        )

        issues: list[str] = []

        if critical:
            issues.append(
                f"{critical} critical IT risk signals require immediate human attention"
            )

        if high:
            issues.append(
                f"{high} high IT risk signals require review"
            )

        if escalation_candidates:
            issues.append(
                f"{escalation_candidates} IT risk signals are escalation candidates"
            )

        if ownerless:
            issues.append(
                f"{ownerless} high or critical risk signals have no assigned owner"
            )

        if not signals:
            issues.append(
                "no IT risk signals are currently available for analysis"
            )

        return ITRiskEscalationAnalysis(
            organization_id=portfolio.organization_id,
            signal_count=len(signals),
            low_risk_count=low,
            normal_risk_count=normal,
            high_risk_count=high,
            critical_risk_count=critical,
            escalation_candidate_count=escalation_candidates,
            ownerless_risk_count=ownerless,
            recommendation_count=len(recommendations),
            top_risk_signal_id=(
                top_signal.signal_id
                if top_signal is not None
                else None
            ),
            top_risk_level=(
                top_signal.level
                if top_signal is not None
                else None
            ),
            recommendations=recommendations,
            issues=tuple(issues),
            requires_human_approval=True,
            executable=False,
        )

    @staticmethod
    def _top_signal(
        signals: tuple[ITRiskSignal, ...],
    ) -> ITRiskSignal | None:
        if not signals:
            return None

        rank = {
            "critical": 4,
            "high": 3,
            "normal": 2,
            "low": 1,
        }

        return max(
            signals,
            key=lambda signal: (
                rank[signal.level],
                signal.escalation_required,
                signal.signal_id,
            ),
        )

    @staticmethod
    def _recommendation_for_signal(
        signal: ITRiskSignal,
    ) -> ITRecommendation:
        if signal.level == "critical":
            priority = "critical"
            action = (
                "Escalate the risk to the appropriate human owner "
                "for review and decision."
            )
        elif signal.level == "high":
            priority = "high"
            action = (
                "Request human review of the affected IT operation "
                "and determine an appropriate response."
            )
        else:
            priority = signal.level
            action = (
                "Review the signal with the responsible human owner "
                "and determine whether escalation is necessary."
            )

        if signal.risk_type in {
            "workload",
            "capacity",
        }:
            action = (
                "Review workload and capacity distribution with the "
                "responsible human owner before making any changes."
            )

        elif signal.risk_type in {
            "dependency",
            "bottleneck",
        }:
            action = (
                "Review the dependency or bottleneck with the "
                "responsible human owner before changing workflow."
            )

        elif signal.risk_type in {
            "deployment",
            "release",
        }:
            action = (
                "Review the deployment or release risk with an "
                "authorized human before taking operational action."
            )

        elif signal.risk_type in {
            "ticket",
            "incident",
            "sla",
        }:
            action = (
                "Review the ticket, incident, or SLA risk with the "
                "responsible human owner and determine the next step."
            )

        return ITRecommendation(
            recommendation_id=f"REC-{signal.signal_id}",
            signal_id=signal.signal_id,
            organization_id=signal.organization_id,
            priority=priority,
            title=f"Review IT risk: {signal.title}",
            rationale=(
                signal.description
                if signal.description
                else (
                    f"The signal is classified as {signal.level} "
                    f"risk in the {signal.risk_type} domain."
                )
            ),
            recommended_action=action,
            requires_human_approval=True,
            executable=False,
        )


def analyze_it_risks(
    portfolio: ITRiskPortfolio,
) -> ITRiskEscalationAnalysis:
    return ITRiskEscalationIntelligence().analyze(portfolio)
