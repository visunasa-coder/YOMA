"""YOMA IT Edition — project and task intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


_ALLOWED_PROJECT_STATUS = {
    "planned",
    "active",
    "on_hold",
    "completed",
    "cancelled",
}

_ALLOWED_TASK_STATUS = {
    "backlog",
    "todo",
    "in_progress",
    "blocked",
    "completed",
    "cancelled",
}

_ALLOWED_PRIORITY = {
    "low",
    "normal",
    "high",
    "critical",
}


@dataclass(frozen=True)
class ITProject:
    project_id: str
    organization_id: str
    name: str
    status: str = "planned"
    owner_id: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("project_id", "organization_id", "name"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        if self.status not in _ALLOWED_PROJECT_STATUS:
            raise ValueError("invalid project status")

        if self.owner_id is not None and (
            not isinstance(self.owner_id, str) or not self.owner_id.strip()
        ):
            raise ValueError("owner_id must be a non-empty string when provided")


@dataclass(frozen=True)
class ITTask:
    task_id: str
    organization_id: str
    project_id: str
    title: str
    status: str = "todo"
    priority: str = "normal"
    assignee_id: str | None = None
    due_at: datetime | None = None
    dependency_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "task_id",
            "organization_id",
            "project_id",
            "title",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        if self.status not in _ALLOWED_TASK_STATUS:
            raise ValueError("invalid task status")

        if self.priority not in _ALLOWED_PRIORITY:
            raise ValueError("invalid task priority")

        if self.assignee_id is not None and (
            not isinstance(self.assignee_id, str) or not self.assignee_id.strip()
        ):
            raise ValueError("assignee_id must be a non-empty string when provided")

        if self.due_at is not None and self.due_at.tzinfo is None:
            raise ValueError("due_at must be timezone-aware")

        if not isinstance(self.dependency_ids, tuple):
            raise ValueError("dependency_ids must be a tuple")


@dataclass(frozen=True)
class ITProjectPortfolio:
    organization_id: str
    projects: tuple[ITProject, ...] = ()
    tasks: tuple[ITTask, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.organization_id, str) or not self.organization_id.strip():
            raise ValueError("organization_id must be a non-empty string")

        if not isinstance(self.projects, tuple):
            raise ValueError("projects must be a tuple")

        if not isinstance(self.tasks, tuple):
            raise ValueError("tasks must be a tuple")

        if any(
            project.organization_id != self.organization_id
            for project in self.projects
        ):
            raise ValueError("all projects must belong to the organization")

        if any(
            task.organization_id != self.organization_id
            for task in self.tasks
        ):
            raise ValueError("all tasks must belong to the organization")

        project_ids = {project.project_id for project in self.projects}

        if any(task.project_id not in project_ids for task in self.tasks):
            raise ValueError("all tasks must reference a known project")


@dataclass(frozen=True)
class ITProjectTaskAnalysis:
    organization_id: str
    project_count: int
    active_project_count: int
    task_count: int
    open_task_count: int
    completed_task_count: int
    blocked_task_count: int
    overdue_task_count: int
    unassigned_task_count: int
    high_priority_open_task_count: int
    dependency_count: int
    issues: tuple[str, ...]
    requires_human_approval: bool = True
    executable: bool = False


class ITProjectTaskIntelligence:
    """Read-only project and task analyzer."""

    def analyze(
        self,
        portfolio: ITProjectPortfolio,
        *,
        now: datetime | None = None,
    ) -> ITProjectTaskAnalysis:
        if not isinstance(portfolio, ITProjectPortfolio):
            raise TypeError("portfolio must be ITProjectPortfolio")

        if now is None:
            now = datetime.now().astimezone()

        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        open_tasks = tuple(
            task
            for task in portfolio.tasks
            if task.status not in {"completed", "cancelled"}
        )

        completed_tasks = tuple(
            task for task in portfolio.tasks if task.status == "completed"
        )

        blocked_tasks = tuple(
            task for task in portfolio.tasks if task.status == "blocked"
        )

        overdue_tasks = tuple(
            task
            for task in open_tasks
            if task.due_at is not None and task.due_at < now
        )

        unassigned_tasks = tuple(
            task for task in open_tasks if task.assignee_id is None
        )

        high_priority_open_tasks = tuple(
            task
            for task in open_tasks
            if task.priority in {"high", "critical"}
        )

        dependency_count = sum(
            len(task.dependency_ids) for task in portfolio.tasks
        )

        issues: list[str] = []

        if overdue_tasks:
            issues.append("open tasks are overdue")

        if unassigned_tasks:
            issues.append("open tasks are unassigned")

        if blocked_tasks:
            issues.append("tasks are blocked")

        if high_priority_open_tasks:
            issues.append("high-priority open work requires attention")

        return ITProjectTaskAnalysis(
            organization_id=portfolio.organization_id,
            project_count=len(portfolio.projects),
            active_project_count=sum(
                project.status == "active"
                for project in portfolio.projects
            ),
            task_count=len(portfolio.tasks),
            open_task_count=len(open_tasks),
            completed_task_count=len(completed_tasks),
            blocked_task_count=len(blocked_tasks),
            overdue_task_count=len(overdue_tasks),
            unassigned_task_count=len(unassigned_tasks),
            high_priority_open_task_count=len(high_priority_open_tasks),
            dependency_count=dependency_count,
            issues=tuple(issues),
        )


def analyze_it_projects(
    portfolio: ITProjectPortfolio,
    *,
    now: datetime | None = None,
) -> ITProjectTaskAnalysis:
    return ITProjectTaskIntelligence().analyze(portfolio, now=now)
