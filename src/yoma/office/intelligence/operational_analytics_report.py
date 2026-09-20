from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping

from yoma.office.intelligence.cross_system_analytics import (
    CrossSystemAnalyticsResult,
)
from yoma.office.intelligence.operational_metrics import (
    OperationalMetricsResult,
)
from yoma.office.intelligence.operational_trend import (
    OperationalTrendResult,
)
from yoma.office.intelligence.bottleneck_detection import (
    BottleneckDetectionResult,
)
from yoma.office.intelligence.cross_system_correlation import (
    CrossSystemCorrelationResult,
)
from yoma.office.intelligence.operational_impact import (
    OperationalImpactResult,
)


@dataclass(frozen=True)
class OperationalAnalyticsReport:
    """Read-only enterprise operational analytics report.

    M35.7 is a composition/reporting layer over M35.1-M35.6.
    It does not execute actions, create approvals, modify policies,
    schedule work, or mutate operational state.
    """

    generated_at: datetime
    analytics: CrossSystemAnalyticsResult
    metrics: OperationalMetricsResult
    trend: OperationalTrendResult
    bottlenecks: BottleneckDetectionResult
    correlations: CrossSystemCorrelationResult
    impact: OperationalImpactResult
    executive_summary: str
    key_findings: tuple[str, ...]
    recommendations: tuple[str, ...]
    read_only: bool = True
    executable: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)


class OperationalAnalyticsReportRuntime:
    """Compose M35.1-M35.6 into one deterministic analytics report."""

    def build(
        self,
        analytics: CrossSystemAnalyticsResult,
        metrics: OperationalMetricsResult,
        trend: OperationalTrendResult,
        bottlenecks: BottleneckDetectionResult,
        correlations: CrossSystemCorrelationResult,
        impact: OperationalImpactResult,
        *,
        generated_at: datetime,
        metadata: Mapping[str, object] | None = None,
    ) -> OperationalAnalyticsReport:
        self._validate_timestamp(generated_at)

        self._validate_component(
            analytics,
            CrossSystemAnalyticsResult,
            "analytics",
        )
        self._validate_component(
            metrics,
            OperationalMetricsResult,
            "metrics",
        )
        self._validate_component(
            trend,
            OperationalTrendResult,
            "trend",
        )
        self._validate_component(
            bottlenecks,
            BottleneckDetectionResult,
            "bottlenecks",
        )
        self._validate_component(
            correlations,
            CrossSystemCorrelationResult,
            "correlations",
        )
        self._validate_component(
            impact,
            OperationalImpactResult,
            "impact",
        )

        executive_summary = self._build_executive_summary(
            analytics,
            metrics,
            impact,
        )

        key_findings = self._build_key_findings(
            analytics,
            metrics,
            trend,
            bottlenecks,
            correlations,
            impact,
        )

        recommendations = self._build_recommendations(
            bottlenecks,
            correlations,
            trend,
        )

        report_metadata = {
            "source": "M35.7",
            "analytics_only": True,
            "composition_only": True,
            "read_only": True,
            "executable": False,
            "estimated_savings_not_observed": True,
        }

        if metadata:
            report_metadata.update(dict(metadata))

        return OperationalAnalyticsReport(
            generated_at=generated_at,
            analytics=analytics,
            metrics=metrics,
            trend=trend,
            bottlenecks=bottlenecks,
            correlations=correlations,
            impact=impact,
            executive_summary=executive_summary,
            key_findings=tuple(key_findings),
            recommendations=tuple(recommendations),
            read_only=True,
            executable=False,
            metadata=report_metadata,
        )

    @staticmethod
    def _validate_timestamp(value: datetime) -> None:
        if not isinstance(value, datetime):
            raise TypeError("generated_at must be a datetime")

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")

    @staticmethod
    def _validate_component(
        value: object,
        expected_type: type,
        name: str,
    ) -> None:
        if not isinstance(value, expected_type):
            raise TypeError(
                f"{name} must be an instance of {expected_type.__name__}"
            )

        if getattr(value, "executable", False):
            raise ValueError(
                f"{name} cannot be executable in M35.7 analytics composition"
            )

    @staticmethod
    def _build_executive_summary(
        analytics: CrossSystemAnalyticsResult,
        metrics: OperationalMetricsResult,
        impact: OperationalImpactResult,
    ) -> str:
        systems = metrics.active_systems
        records = analytics.total_records
        hours = impact.estimated_time_saved_hours

        return (
            f"Observed {records} operational records across "
            f"{systems} active systems. "
            f"Estimated manual effort is "
            f"{impact.estimated_manual_minutes:.2f} minutes, "
            f"with an estimated {hours:.2f} hours of potential time saved. "
            f"These savings are estimates and are not claims of observed savings."
        )

    @staticmethod
    def _build_key_findings(
        analytics: CrossSystemAnalyticsResult,
        metrics: OperationalMetricsResult,
        trend: OperationalTrendResult,
        bottlenecks: BottleneckDetectionResult,
        correlations: CrossSystemCorrelationResult,
        impact: OperationalImpactResult,
    ) -> list[str]:
        findings: list[str] = []

        findings.append(
            f"{analytics.total_records} records observed across "
            f"{metrics.active_systems} active systems."
        )

        if metrics.records_per_hour > 0:
            findings.append(
                f"Operational activity averaged "
                f"{metrics.records_per_hour:.2f} records per hour."
            )
        else:
            findings.append("No positive operational activity rate was observed.")

        if bottlenecks.candidates:
            names = ", ".join(
                candidate.source_system
                for candidate in bottlenecks.candidates
            )
            findings.append(
                f"Potential operational concentration detected in: {names}."
            )
        else:
            findings.append("No operational bottleneck candidates were detected.")

        if correlations.correlations:
            strongest = correlations.correlations[0]
            findings.append(
                f"Strongest cross-system relationship was observed between "
                f"{strongest.source_system} and {strongest.related_system} "
                f"at a {strongest.correlation_rate:.2%} correlation rate."
            )
        else:
            findings.append("No cross-system correlations were detected.")

        if trend.trends:
            for item in trend.trends:
                findings.append(
                    f"{item.metric} trend is {item.direction}."
                )

        findings.append(
            f"Potential time savings are estimated at "
            f"{impact.estimated_time_saved_hours:.2f} hours; "
            f"this is an analytical estimate rather than observed savings."
        )

        return findings

    @staticmethod
    def _build_recommendations(
        bottlenecks: BottleneckDetectionResult,
        correlations: CrossSystemCorrelationResult,
        trend: OperationalTrendResult,
    ) -> list[str]:
        recommendations: list[str] = []

        if bottlenecks.candidates:
            recommendations.append(
                "Review high-activity systems for process concentration "
                "and potential workflow optimization."
            )

        if correlations.correlations:
            recommendations.append(
                "Review correlated cross-system activity for opportunities "
                "to reduce duplicated operational effort."
            )

        increasing = [
            item
            for item in trend.trends
            if item.direction == "increasing"
        ]

        if increasing:
            recommendations.append(
                "Review increasing operational trends for emerging "
                "capacity or workload requirements."
            )

        if not recommendations:
            recommendations.append(
                "Continue collecting operational observations to establish "
                "a stronger analytical baseline."
            )

        return recommendations
