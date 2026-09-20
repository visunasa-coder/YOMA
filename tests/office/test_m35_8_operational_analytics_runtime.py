from datetime import datetime, timezone, timedelta

import pytest

from yoma.office.intelligence.cross_system_analytics import (
    AnalyticsRecord,
    CrossSystemAnalyticsRuntime,
)
from yoma.office.intelligence.operational_metrics import (
    OperationalMetricsRuntime,
)
from yoma.office.intelligence.operational_trend import (
    OperationalTrendRuntime,
)
from yoma.office.intelligence.bottleneck_detection import (
    BottleneckDetectionRuntime,
)
from yoma.office.intelligence.cross_system_correlation import (
    CrossSystemCorrelationRuntime,
)
from yoma.office.intelligence.operational_impact import (
    OperationalImpactRuntime,
)
from yoma.office.intelligence.operational_analytics_report import (
    OperationalAnalyticsReport,
    OperationalAnalyticsReportRuntime,
)
from yoma.office.intelligence.operational_analytics_runtime import (
    OperationalAnalyticsResult,
    OperationalAnalyticsRuntime,
)


BASE = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)


def make_records():
    return (
        AnalyticsRecord(
            record_id="r1",
            source_system="calendar",
            record_type="event",
            observed_at=BASE,
            organization_id="org-1",
            user_id="user-1",
        ),
        AnalyticsRecord(
            record_id="r2",
            source_system="gmail",
            record_type="message",
            observed_at=BASE + timedelta(minutes=10),
            organization_id="org-1",
            user_id="user-1",
        ),
        AnalyticsRecord(
            record_id="r3",
            source_system="calendar",
            record_type="event",
            observed_at=BASE + timedelta(minutes=20),
            organization_id="org-1",
            user_id="user-1",
        ),
        AnalyticsRecord(
            record_id="r4",
            source_system="slack",
            record_type="message",
            observed_at=BASE + timedelta(minutes=30),
            organization_id="org-1",
            user_id="user-1",
        ),
    )


def build_report():
    records = make_records()

    analytics = CrossSystemAnalyticsRuntime().analyze(
        records,
        window_start=BASE - timedelta(hours=1),
        window_end=BASE + timedelta(hours=2),
    )

    metrics = OperationalMetricsRuntime().analyze(records)

    trend = OperationalTrendRuntime().analyze(
        records,
        period="hour",
    )

    bottlenecks = BottleneckDetectionRuntime().analyze(
        records,
        threshold_multiplier=1.0,
    )

    correlations = CrossSystemCorrelationRuntime().analyze(
        records,
        window_seconds=900,
    )

    impact = OperationalImpactRuntime().analyze(records)

    return OperationalAnalyticsReportRuntime().build(
        analytics,
        metrics,
        trend,
        bottlenecks,
        correlations,
        impact,
        generated_at=BASE + timedelta(hours=3),
    )


def test_builds_final_result():
    report = build_report()

    result = OperationalAnalyticsRuntime().build(report)

    assert isinstance(result, OperationalAnalyticsResult)
    assert result.report is report


def test_complete_m35_chain_is_validated():
    result = OperationalAnalyticsRuntime().build(build_report())

    assert result.validated is True
    assert result.validation_errors == ()


def test_m35_outputs_are_preserved():
    report = build_report()
    result = OperationalAnalyticsRuntime().build(report)

    assert result.report.analytics is report.analytics
    assert result.report.metrics is report.metrics
    assert result.report.trend is report.trend
    assert result.report.bottlenecks is report.bottlenecks
    assert result.report.correlations is report.correlations
    assert result.report.impact is report.impact


def test_final_result_is_read_only():
    result = OperationalAnalyticsRuntime().build(build_report())

    assert result.read_only is True
    assert result.executable is False


def test_final_metadata_declares_m35_8():
    result = OperationalAnalyticsRuntime().build(build_report())

    assert result.metadata["source"] == "M35.8"
    assert result.metadata["analytics_only"] is True
    assert result.metadata["composition_only"] is True
    assert result.metadata["validation_only"] is True


def test_estimated_savings_boundary_is_preserved():
    result = OperationalAnalyticsRuntime().build(build_report())

    assert result.metadata["estimated_savings_not_observed"] is True
    assert (
        result.report.metadata["estimated_savings_not_observed"]
        is True
    )


def test_custom_metadata_is_preserved():
    result = OperationalAnalyticsRuntime().build(
        build_report(),
        metadata={"pilot": "14-day", "team_size": 10},
    )

    assert result.metadata["pilot"] == "14-day"
    assert result.metadata["team_size"] == 10


def test_rejects_non_report_input():
    result = OperationalAnalyticsRuntime().build(object())

    assert result.validated is False
    assert "report must be an OperationalAnalyticsReport" in (
        result.validation_errors
    )


def test_detects_non_read_only_report():
    report = build_report()
    object.__setattr__(report, "read_only", False)

    result = OperationalAnalyticsRuntime().build(report)

    assert result.validated is False
    assert "report must be read-only" in result.validation_errors


def test_detects_executable_report():
    report = build_report()
    object.__setattr__(report, "executable", True)

    result = OperationalAnalyticsRuntime().build(report)

    assert result.validated is False
    assert "report must be non-executable" in result.validation_errors


def test_validation_is_deterministic():
    report = build_report()
    runtime = OperationalAnalyticsRuntime()

    first = runtime.build(report)
    second = runtime.build(report)

    assert first.validated == second.validated
    assert first.validation_errors == second.validation_errors
    assert dict(first.metadata) == dict(second.metadata)


def test_no_execution_capability_is_introduced():
    result = OperationalAnalyticsRuntime().build(build_report())

    assert not hasattr(result, "execute")
    assert not hasattr(result, "approve")
    assert not hasattr(result, "schedule")
    assert result.executable is False
