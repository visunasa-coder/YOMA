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


def build_components():
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

    return (
        analytics,
        metrics,
        trend,
        bottlenecks,
        correlations,
        impact,
    )


def test_builds_complete_report():
    components = build_components()

    report = OperationalAnalyticsReportRuntime().build(
        *components,
        generated_at=BASE + timedelta(hours=3),
    )

    assert isinstance(report, OperationalAnalyticsReport)
    assert report.analytics is components[0]
    assert report.metrics is components[1]
    assert report.trend is components[2]
    assert report.bottlenecks is components[3]
    assert report.correlations is components[4]
    assert report.impact is components[5]


def test_report_is_read_only():
    report = OperationalAnalyticsReportRuntime().build(
        *build_components(),
        generated_at=BASE,
    )

    assert report.read_only is True
    assert report.executable is False


def test_report_metadata_declares_analytics_only():
    report = OperationalAnalyticsReportRuntime().build(
        *build_components(),
        generated_at=BASE,
    )

    assert report.metadata["source"] == "M35.7"
    assert report.metadata["analytics_only"] is True
    assert report.metadata["composition_only"] is True
    assert report.metadata["read_only"] is True
    assert report.metadata["executable"] is False


def test_custom_metadata_is_preserved():
    report = OperationalAnalyticsReportRuntime().build(
        *build_components(),
        generated_at=BASE,
        metadata={"pilot": "14-day", "team_size": 10},
    )

    assert report.metadata["pilot"] == "14-day"
    assert report.metadata["team_size"] == 10


def test_executive_summary_contains_core_metrics():
    components = build_components()

    report = OperationalAnalyticsReportRuntime().build(
        *components,
        generated_at=BASE,
    )

    assert "4 operational records" in report.executive_summary
    assert "3 active systems" in report.executive_summary
    assert "estimated" in report.executive_summary.lower()


def test_key_findings_are_generated():
    report = OperationalAnalyticsReportRuntime().build(
        *build_components(),
        generated_at=BASE,
    )

    assert report.key_findings
    assert all(isinstance(item, str) for item in report.key_findings)


def test_recommendations_are_generated():
    report = OperationalAnalyticsReportRuntime().build(
        *build_components(),
        generated_at=BASE,
    )

    assert report.recommendations
    assert all(isinstance(item, str) for item in report.recommendations)


def test_estimated_savings_are_not_presented_as_observed():
    report = OperationalAnalyticsReportRuntime().build(
        *build_components(),
        generated_at=BASE,
    )

    assert report.metadata["estimated_savings_not_observed"] is True
    assert "not claims of observed savings" in report.executive_summary


def test_requires_timezone_aware_generated_at():
    with pytest.raises(ValueError, match="timezone-aware"):
        OperationalAnalyticsReportRuntime().build(
            *build_components(),
            generated_at=datetime(2026, 9, 1, 10, 0),
        )


def test_rejects_wrong_component_type():
    components = list(build_components())
    components[0] = object()

    with pytest.raises(TypeError, match="analytics"):
        OperationalAnalyticsReportRuntime().build(
            *components,
            generated_at=BASE,
        )


def test_report_generation_is_deterministic():
    components = build_components()

    runtime = OperationalAnalyticsReportRuntime()

    first = runtime.build(
        *components,
        generated_at=BASE,
    )

    second = runtime.build(
        *components,
        generated_at=BASE,
    )

    assert first.executive_summary == second.executive_summary
    assert first.key_findings == second.key_findings
    assert first.recommendations == second.recommendations
    assert dict(first.metadata) == dict(second.metadata)


def test_component_execution_invariant_is_enforced():
    components = list(build_components())

    class FakeExecutable:
        executable = True

    components[0] = FakeExecutable()

    with pytest.raises(TypeError, match="analytics"):
        OperationalAnalyticsReportRuntime().build(
            *components,
            generated_at=BASE,
        )
