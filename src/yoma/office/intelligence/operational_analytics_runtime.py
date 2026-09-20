from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from yoma.office.intelligence.operational_analytics_report import (
    OperationalAnalyticsReport,
)


@dataclass(frozen=True)
class OperationalAnalyticsResult:
    """Final M35 analytics composition and validation result."""

    report: OperationalAnalyticsReport
    validated: bool
    validation_errors: tuple[str, ...] = ()
    read_only: bool = True
    executable: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)


class OperationalAnalyticsRuntime:
    """Final read-only validation boundary for M35 analytics."""

    def build(
        self,
        report: OperationalAnalyticsReport,
        *,
        metadata: Mapping[str, object] | None = None,
    ) -> OperationalAnalyticsResult:
        errors = self._validate(report)

        result_metadata = {
            "source": "M35.8",
            "analytics_only": True,
            "composition_only": True,
            "validation_only": True,
            "read_only": True,
            "executable": False,
            "estimated_savings_not_observed": True,
        }

        if metadata:
            result_metadata.update(dict(metadata))

        return OperationalAnalyticsResult(
            report=report,
            validated=not errors,
            validation_errors=tuple(errors),
            read_only=True,
            executable=False,
            metadata=result_metadata,
        )

    @staticmethod
    def _validate(
        report: OperationalAnalyticsReport,
    ) -> list[str]:
        errors: list[str] = []

        if not isinstance(report, OperationalAnalyticsReport):
            return ["report must be an OperationalAnalyticsReport"]

        if report.read_only is not True:
            errors.append("report must be read-only")

        if report.executable is not False:
            errors.append("report must be non-executable")

        components = (
            ("M35.1", report.analytics),
            ("M35.2", report.metrics),
            ("M35.3", report.trend),
            ("M35.4", report.bottlenecks),
            ("M35.5", report.correlations),
            ("M35.6", report.impact),
        )

        for source, component in components:
            if getattr(component, "read_only", True) is not True:
                errors.append(f"{source} component must be read-only")

            if getattr(component, "executable", False) is not False:
                errors.append(f"{source} component must be non-executable")

            if getattr(component, "metadata", {}).get("source") != source:
                errors.append(
                    f"{source} component metadata source is invalid"
                )

        if report.metadata.get("source") != "M35.7":
            errors.append("report metadata source is invalid")

        if report.metadata.get("analytics_only") is not True:
            errors.append("report must declare analytics_only")

        if report.metadata.get("composition_only") is not True:
            errors.append("report must declare composition_only")

        if report.metadata.get("estimated_savings_not_observed") is not True:
            errors.append(
                "estimated savings must not be represented as observed savings"
            )

        return errors
