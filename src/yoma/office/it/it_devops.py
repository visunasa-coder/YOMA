"""YOMA IT Edition - DevOps deployment and release intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


_DEPLOYMENT_STATUSES = {
    "planned",
    "in_progress",
    "succeeded",
    "failed",
    "rolled_back",
    "cancelled",
}

_RELEASE_STATUSES = {
    "draft",
    "scheduled",
    "released",
    "failed",
    "rolled_back",
    "cancelled",
}

_ENVIRONMENTS = {
    "development",
    "testing",
    "staging",
    "production",
}

_RISK_LEVELS = {"low", "normal", "high", "critical"}


@dataclass(frozen=True)
class ITDeployment:
    deployment_id: str
    organization_id: str
    service_id: str
    version: str
    environment: str
    status: str = "planned"
    owner_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    rollback_required: bool = False
    risk: str = "normal"

    def __post_init__(self):
        for name in (
            "deployment_id",
            "organization_id",
            "service_id",
            "version",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

        if self.environment not in _ENVIRONMENTS:
            raise ValueError("invalid deployment environment")

        if self.status not in _DEPLOYMENT_STATUSES:
            raise ValueError("invalid deployment status")

        if self.risk not in _RISK_LEVELS:
            raise ValueError("invalid deployment risk")

        if self.owner_id is not None and (
            not isinstance(self.owner_id, str) or not self.owner_id.strip()
        ):
            raise ValueError("owner_id must be a non-empty string when provided")

        for name in ("started_at", "completed_at"):
            value = getattr(self, name)
            if value is not None and value.tzinfo is None:
                raise ValueError(f"{name} must be timezone-aware")

        if not isinstance(self.rollback_required, bool):
            raise ValueError("rollback_required must be boolean")


@dataclass(frozen=True)
class ITRelease:
    release_id: str
    organization_id: str
    service_id: str
    version: str
    status: str = "draft"
    owner_id: str | None = None
    target_environment: str = "production"
    risk: str = "normal"

    def __post_init__(self):
        for name in (
            "release_id",
            "organization_id",
            "service_id",
            "version",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")

        if self.status not in _RELEASE_STATUSES:
            raise ValueError("invalid release status")

        if self.target_environment not in _ENVIRONMENTS:
            raise ValueError("invalid target environment")

        if self.risk not in _RISK_LEVELS:
            raise ValueError("invalid release risk")

        if self.owner_id is not None and (
            not isinstance(self.owner_id, str) or not self.owner_id.strip()
        ):
            raise ValueError("owner_id must be a non-empty string when provided")


@dataclass(frozen=True)
class ITDevOpsPortfolio:
    organization_id: str
    deployments: tuple[ITDeployment, ...] = ()
    releases: tuple[ITRelease, ...] = ()

    def __post_init__(self):
        if not isinstance(self.organization_id, str) or not self.organization_id.strip():
            raise ValueError("organization_id must be a non-empty string")

        if not isinstance(self.deployments, tuple):
            raise ValueError("deployments must be a tuple")

        if not isinstance(self.releases, tuple):
            raise ValueError("releases must be a tuple")

        for deployment in self.deployments:
            if deployment.organization_id != self.organization_id:
                raise ValueError(
                    "all deployments must belong to the organization"
                )

        for release in self.releases:
            if release.organization_id != self.organization_id:
                raise ValueError(
                    "all releases must belong to the organization"
                )


@dataclass(frozen=True)
class ITDevOpsAnalysis:
    organization_id: str
    deployment_count: int
    active_deployment_count: int
    failed_deployment_count: int
    production_deployment_count: int
    rollback_candidate_count: int
    unowned_deployment_count: int
    release_count: int
    active_release_count: int
    failed_release_count: int
    production_release_count: int
    high_risk_change_count: int
    unowned_release_count: int
    issues: tuple[str, ...]
    requires_human_approval: bool = True
    executable: bool = False


class ITDevOpsIntelligence:
    """Read-only DevOps deployment and release analyzer."""

    def analyze(
        self,
        portfolio: ITDevOpsPortfolio,
    ) -> ITDevOpsAnalysis:
        if not isinstance(portfolio, ITDevOpsPortfolio):
            raise TypeError("portfolio must be ITDevOpsPortfolio")

        active_deployments = tuple(
            item
            for item in portfolio.deployments
            if item.status in {"planned", "in_progress"}
        )

        failed_deployments = tuple(
            item
            for item in portfolio.deployments
            if item.status == "failed"
        )

        production_deployments = tuple(
            item
            for item in portfolio.deployments
            if item.environment == "production"
        )

        rollback_candidates = tuple(
            item
            for item in portfolio.deployments
            if item.rollback_required
            or item.status == "rolled_back"
        )

        unowned_deployments = tuple(
            item
            for item in active_deployments
            if item.owner_id is None
        )

        active_releases = tuple(
            item
            for item in portfolio.releases
            if item.status in {"draft", "scheduled"}
        )

        failed_releases = tuple(
            item
            for item in portfolio.releases
            if item.status == "failed"
        )

        production_releases = tuple(
            item
            for item in portfolio.releases
            if item.target_environment == "production"
        )

        high_risk_changes = tuple(
            item
            for item in portfolio.deployments
            if item.risk in {"high", "critical"}
        )

        high_risk_changes += tuple(
            item
            for item in portfolio.releases
            if item.risk in {"high", "critical"}
        )

        unowned_releases = tuple(
            item
            for item in active_releases
            if item.owner_id is None
        )

        issues: list[str] = []

        if failed_deployments:
            issues.append("failed deployments require investigation")

        if rollback_candidates:
            issues.append("deployments indicate rollback attention")

        if unowned_deployments:
            issues.append("active deployments have no assigned owner")

        if failed_releases:
            issues.append("failed releases require investigation")

        if high_risk_changes:
            issues.append("high-risk changes require human review")

        if unowned_releases:
            issues.append("active releases have no assigned owner")

        return ITDevOpsAnalysis(
            organization_id=portfolio.organization_id,
            deployment_count=len(portfolio.deployments),
            active_deployment_count=len(active_deployments),
            failed_deployment_count=len(failed_deployments),
            production_deployment_count=len(production_deployments),
            rollback_candidate_count=len(rollback_candidates),
            unowned_deployment_count=len(unowned_deployments),
            release_count=len(portfolio.releases),
            active_release_count=len(active_releases),
            failed_release_count=len(failed_releases),
            production_release_count=len(production_releases),
            high_risk_change_count=len(high_risk_changes),
            unowned_release_count=len(unowned_releases),
            issues=tuple(issues),
        )


def analyze_it_devops(
    portfolio: ITDevOpsPortfolio,
) -> ITDevOpsAnalysis:
    return ITDevOpsIntelligence().analyze(portfolio)
