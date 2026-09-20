"""Dedicated tests for YOMA IT Edition M44.2."""

from datetime import datetime, timezone

from yoma.office.it.it_projects import (
    ITProject,
    ITProjectPortfolio,
    ITProjectTaskIntelligence,
    ITTask,
)


def test_project_creation():
    project = ITProject("p1", "org-1", "Platform Upgrade")
    assert project.name == "Platform Upgrade"


def test_invalid_project_status_rejected():
    try:
        ITProject("p1", "org-1", "Project", status="unknown")
        assert False
    except ValueError:
        assert True


def test_task_creation():
    task = ITTask(
        "t1",
        "org-1",
        "p1",
        "Implement API",
    )
    assert task.status == "todo"


def test_invalid_task_status_rejected():
    try:
        ITTask(
            "t1",
            "org-1",
            "p1",
            "Task",
            status="unknown",
        )
        assert False
    except ValueError:
        assert True


def test_invalid_priority_rejected():
    try:
        ITTask(
            "t1",
            "org-1",
            "p1",
            "Task",
            priority="urgent",
        )
        assert False
    except ValueError:
        assert True


def test_due_date_must_be_timezone_aware():
    try:
        ITTask(
            "t1",
            "org-1",
            "p1",
            "Task",
            due_at=datetime(2026, 9, 1),
        )
        assert False
    except ValueError:
        assert True


def test_portfolio_requires_known_project():
    try:
        ITProjectPortfolio(
            "org-1",
            projects=(),
            tasks=(
                ITTask("t1", "org-1", "missing", "Task"),
            ),
        )
        assert False
    except ValueError:
        assert True


def test_portfolio_counts():
    portfolio = ITProjectPortfolio(
        "org-1",
        projects=(
            ITProject("p1", "org-1", "Project", status="active"),
        ),
        tasks=(
            ITTask("t1", "org-1", "p1", "Task 1"),
            ITTask("t2", "org-1", "p1", "Task 2", status="completed"),
        ),
    )

    result = ITProjectTaskIntelligence().analyze(portfolio)

    assert result.project_count == 1
    assert result.active_project_count == 1
    assert result.task_count == 2
    assert result.open_task_count == 1
    assert result.completed_task_count == 1


def test_blocked_tasks_detected():
    portfolio = ITProjectPortfolio(
        "org-1",
        projects=(ITProject("p1", "org-1", "Project"),),
        tasks=(
            ITTask("t1", "org-1", "p1", "Blocked task", status="blocked"),
        ),
    )

    result = ITProjectTaskIntelligence().analyze(portfolio)

    assert result.blocked_task_count == 1
    assert "tasks are blocked" in result.issues


def test_unassigned_tasks_detected():
    portfolio = ITProjectPortfolio(
        "org-1",
        projects=(ITProject("p1", "org-1", "Project"),),
        tasks=(
            ITTask("t1", "org-1", "p1", "Unassigned task"),
        ),
    )

    result = ITProjectTaskIntelligence().analyze(portfolio)

    assert result.unassigned_task_count == 1


def test_overdue_tasks_detected():
    now = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)

    portfolio = ITProjectPortfolio(
        "org-1",
        projects=(ITProject("p1", "org-1", "Project"),),
        tasks=(
            ITTask(
                "t1",
                "org-1",
                "p1",
                "Overdue task",
                due_at=datetime(2026, 9, 5, 12, tzinfo=timezone.utc),
            ),
        ),
    )

    result = ITProjectTaskIntelligence().analyze(portfolio, now=now)

    assert result.overdue_task_count == 1
    assert "open tasks are overdue" in result.issues


def test_high_priority_work_detected():
    portfolio = ITProjectPortfolio(
        "org-1",
        projects=(ITProject("p1", "org-1", "Project"),),
        tasks=(
            ITTask(
                "t1",
                "org-1",
                "p1",
                "Critical task",
                priority="critical",
            ),
        ),
    )

    result = ITProjectTaskIntelligence().analyze(portfolio)

    assert result.high_priority_open_task_count == 1


def test_dependencies_are_counted():
    portfolio = ITProjectPortfolio(
        "org-1",
        projects=(ITProject("p1", "org-1", "Project"),),
        tasks=(
            ITTask(
                "t1",
                "org-1",
                "p1",
                "Task",
                dependency_ids=("t0", "t-1"),
            ),
        ),
    )

    result = ITProjectTaskIntelligence().analyze(portfolio)

    assert result.dependency_count == 2


def test_safety_boundary_remains_intact():
    portfolio = ITProjectPortfolio("org-1")

    result = ITProjectTaskIntelligence().analyze(portfolio)

    assert result.requires_human_approval is True
    assert result.executable is False


def test_analysis_is_deterministic():
    portfolio = ITProjectPortfolio(
        "org-1",
        projects=(ITProject("p1", "org-1", "Project"),),
        tasks=(ITTask("t1", "org-1", "p1", "Task"),),
    )

    intelligence = ITProjectTaskIntelligence()

    assert intelligence.analyze(portfolio) == intelligence.analyze(portfolio)


def test_helper_functional_surface():
    portfolio = ITProjectPortfolio(
        "org-1",
        projects=(ITProject("p1", "org-1", "Project"),),
    )

    result = ITProjectTaskIntelligence().analyze(portfolio)

    assert result.organization_id == "org-1"


def test_invalid_input_type_rejected():
    try:
        ITProjectTaskIntelligence().analyze("invalid")
        assert False
    except TypeError:
        assert True
