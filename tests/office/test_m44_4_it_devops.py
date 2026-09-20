from yoma.office.it.it_devops import (
    ITDeployment,
    ITDevOpsIntelligence,
    ITDevOpsPortfolio,
    ITRelease,
)


def test_deployment_creation():
    deployment = ITDeployment(
        "d1",
        "org-1",
        "svc-1",
        "v1.0",
        "production",
    )
    assert deployment.environment == "production"


def test_invalid_deployment_environment():
    try:
        ITDeployment(
            "d1",
            "org-1",
            "svc-1",
            "v1.0",
            "unknown",
        )
        assert False
    except ValueError:
        assert True


def test_invalid_deployment_status():
    try:
        ITDeployment(
            "d1",
            "org-1",
            "svc-1",
            "v1.0",
            "production",
            status="unknown",
        )
        assert False
    except ValueError:
        assert True


def test_invalid_deployment_risk():
    try:
        ITDeployment(
            "d1",
            "org-1",
            "svc-1",
            "v1.0",
            "production",
            risk="urgent",
        )
        assert False
    except ValueError:
        assert True


def test_release_creation():
    release = ITRelease(
        "r1",
        "org-1",
        "svc-1",
        "v2.0",
        target_environment="production",
    )
    assert release.target_environment == "production"


def test_invalid_release_status():
    try:
        ITRelease(
            "r1",
            "org-1",
            "svc-1",
            "v1.0",
            status="unknown",
        )
        assert False
    except ValueError:
        assert True


def test_invalid_release_environment():
    try:
        ITRelease(
            "r1",
            "org-1",
            "svc-1",
            "v1.0",
            target_environment="unknown",
        )
        assert False
    except ValueError:
        assert True


def test_portfolio_requires_matching_organization():
    try:
        ITDevOpsPortfolio(
            "org-1",
            deployments=(
                ITDeployment(
                    "d1",
                    "org-2",
                    "svc-1",
                    "v1",
                    "production",
                ),
            ),
        )
        assert False
    except ValueError:
        assert True


def test_deployment_counts():
    portfolio = ITDevOpsPortfolio(
        "org-1",
        deployments=(
            ITDeployment(
                "d1",
                "org-1",
                "svc-1",
                "v1",
                "production",
                status="in_progress",
            ),
            ITDeployment(
                "d2",
                "org-1",
                "svc-1",
                "v2",
                "staging",
                status="failed",
            ),
        ),
    )

    result = ITDevOpsIntelligence().analyze(portfolio)

    assert result.deployment_count == 2
    assert result.active_deployment_count == 1
    assert result.failed_deployment_count == 1
    assert result.production_deployment_count == 1


def test_failed_deployment_detected():
    portfolio = ITDevOpsPortfolio(
        "org-1",
        deployments=(
            ITDeployment(
                "d1",
                "org-1",
                "svc-1",
                "v1",
                "production",
                status="failed",
            ),
        ),
    )

    result = ITDevOpsIntelligence().analyze(portfolio)

    assert result.failed_deployment_count == 1
    assert "failed deployments require investigation" in result.issues


def test_rollback_candidate_detected():
    portfolio = ITDevOpsPortfolio(
        "org-1",
        deployments=(
            ITDeployment(
                "d1",
                "org-1",
                "svc-1",
                "v1",
                "production",
                rollback_required=True,
            ),
        ),
    )

    result = ITDevOpsIntelligence().analyze(portfolio)

    assert result.rollback_candidate_count == 1


def test_unowned_deployment_detected():
    portfolio = ITDevOpsPortfolio(
        "org-1",
        deployments=(
            ITDeployment(
                "d1",
                "org-1",
                "svc-1",
                "v1",
                "production",
                status="in_progress",
            ),
        ),
    )

    result = ITDevOpsIntelligence().analyze(portfolio)

    assert result.unowned_deployment_count == 1


def test_release_counts():
    portfolio = ITDevOpsPortfolio(
        "org-1",
        releases=(
            ITRelease(
                "r1",
                "org-1",
                "svc-1",
                "v1",
                status="scheduled",
                target_environment="production",
            ),
            ITRelease(
                "r2",
                "org-1",
                "svc-1",
                "v2",
                status="failed",
                    target_environment="staging",
            ),
        ),
    )

    result = ITDevOpsIntelligence().analyze(portfolio)

    assert result.release_count == 2
    assert result.active_release_count == 1
    assert result.failed_release_count == 1
    assert result.production_release_count == 1


def test_high_risk_changes_detected():
    portfolio = ITDevOpsPortfolio(
        "org-1",
        deployments=(
            ITDeployment(
                "d1",
                "org-1",
                "svc-1",
                "v1",
                "production",
                risk="critical",
            ),
        ),
        releases=(
            ITRelease(
                "r1",
                "org-1",
                "svc-1",
                "v1",
                risk="high",
            ),
        ),
    )

    result = ITDevOpsIntelligence().analyze(portfolio)

    assert result.high_risk_change_count == 2


def test_unowned_release_detected():
    portfolio = ITDevOpsPortfolio(
        "org-1",
        releases=(
            ITRelease(
                "r1",
                "org-1",
                "svc-1",
                "v1",
                status="scheduled",
            ),
        ),
    )

    result = ITDevOpsIntelligence().analyze(portfolio)

    assert result.unowned_release_count == 1


def test_safety_boundary():
    result = ITDevOpsIntelligence().analyze(
        ITDevOpsPortfolio("org-1")
    )

    assert result.requires_human_approval is True
    assert result.executable is False


def test_analysis_is_deterministic():
    portfolio = ITDevOpsPortfolio(
        "org-1",
        deployments=(
            ITDeployment(
                "d1",
                "org-1",
                "svc-1",
                "v1",
                "production",
            ),
        ),
    )

    intelligence = ITDevOpsIntelligence()

    assert intelligence.analyze(portfolio) == intelligence.analyze(portfolio)


def test_invalid_input_type_rejected():
    try:
        ITDevOpsIntelligence().analyze("invalid")
        assert False
    except TypeError:
        assert True
