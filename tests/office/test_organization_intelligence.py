from datetime import datetime, timezone

import pytest

from yoma.office.identity import SystemIdentity, UserIdentity
from yoma.office.intelligence.organization import OrganizationIntelligence


def make_users():
    return [
        UserIdentity(
            user_id="EMP001",
            name="Vishal",
            department="Research",
            role="Developer",
            active=True,
        ),
        UserIdentity(
            user_id="EMP002",
            name="Employee Two",
            department="Engineering",
            role="Developer",
            active=True,
        ),
        UserIdentity(
            user_id="EMP003",
            name="Employee Three",
            department="Research",
            role="Manager",
            active=False,
        ),
    ]


def make_systems():
    return [
        SystemIdentity(
            system_id="SYS001",
            name="Central Server",
            system_number="001",
            active=True,
        ),
        SystemIdentity(
            system_id="SYS002",
            name="Backup Server",
            system_number="002",
            active=False,
        ),
    ]


def test_creates_organization_intelligence():
    intelligence = OrganizationIntelligence(
        users=make_users(),
        systems=make_systems(),
    )

    assert intelligence is not None


def test_counts_total_users():
    intelligence = OrganizationIntelligence(
        users=make_users(),
        systems=make_systems(),
    )

    assert intelligence.total_users() == 3


def test_counts_active_users():
    intelligence = OrganizationIntelligence(
        users=make_users(),
        systems=make_systems(),
    )

    assert intelligence.active_users() == 2


def test_counts_inactive_users():
    intelligence = OrganizationIntelligence(
        users=make_users(),
        systems=make_systems(),
    )

    assert intelligence.inactive_users() == 1


def test_counts_total_systems():
    intelligence = OrganizationIntelligence(
        users=make_users(),
        systems=make_systems(),
    )

    assert intelligence.total_systems() == 2


def test_counts_active_systems():
    intelligence = OrganizationIntelligence(
        users=make_users(),
        systems=make_systems(),
    )

    assert intelligence.active_systems() == 1


def test_counts_inactive_systems():
    intelligence = OrganizationIntelligence(
        users=make_users(),
        systems=make_systems(),
    )

    assert intelligence.inactive_systems() == 1


def test_lists_departments_deterministically():
    intelligence = OrganizationIntelligence(
        users=make_users(),
        systems=make_systems(),
    )

    assert intelligence.departments() == [
        "Engineering",
        "Research",
    ]


def test_counts_users_by_department():
    intelligence = OrganizationIntelligence(
        users=make_users(),
        systems=make_systems(),
    )

    assert intelligence.users_by_department() == {
        "Engineering": 1,
        "Research": 2,
    }


def test_lists_roles_deterministically():
    intelligence = OrganizationIntelligence(
        users=make_users(),
        systems=make_systems(),
    )

    assert intelligence.roles() == [
        "Developer",
        "Manager",
    ]


def test_counts_users_by_role():
    intelligence = OrganizationIntelligence(
        users=make_users(),
        systems=make_systems(),
    )

    assert intelligence.users_by_role() == {
        "Developer": 2,
        "Manager": 1,
    }


def test_snapshot_returns_organization_metrics():
    intelligence = OrganizationIntelligence(
        users=make_users(),
        systems=make_systems(),
    )

    snapshot = intelligence.snapshot()

    assert snapshot["total_users"] == 3
    assert snapshot["active_users"] == 2
    assert snapshot["inactive_users"] == 1
    assert snapshot["total_systems"] == 2
    assert snapshot["active_systems"] == 1
    assert snapshot["inactive_systems"] == 1
    assert snapshot["departments"] == [
        "Engineering",
        "Research",
    ]
    assert snapshot["roles"] == [
        "Developer",
        "Manager",
    ]


def test_invalid_users_collection_rejected():
    with pytest.raises(TypeError):
        OrganizationIntelligence(
            users="invalid",
            systems=make_systems(),
        )


def test_invalid_systems_collection_rejected():
    with pytest.raises(TypeError):
        OrganizationIntelligence(
            users=make_users(),
            systems="invalid",
        )