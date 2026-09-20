import pytest

from yoma.office.central_server import CentralServerAdapter


def make_adapter():
    return CentralServerAdapter(
        name="company-central-server",
    )


def test_normalize_user_record():
    adapter = make_adapter()

    result = adapter.normalize_user(
        {
            "id": "EMP001",
            "name": "Vishal",
            "username": "vishal",
            "email": "vishal@example.com",
            "department": "Research",
            "role": "Employee",
            "system_id": "SYS001",
        }
    )

    assert result.user_id == "EMP001"
    assert result.name == "Vishal"
    assert result.username == "vishal"
    assert result.email == "vishal@example.com"
    assert result.department == "Research"
    assert result.role == "Employee"
    assert result.system_id == "SYS001"
    assert result.active is True


def test_normalize_user_preserves_inactive_state():
    adapter = make_adapter()

    result = adapter.normalize_user(
        {
            "id": "EMP002",
            "name": "Former Employee",
            "active": False,
        }
    )

    assert result.user_id == "EMP002"
    assert result.active is False


def test_normalize_user_allows_missing_optional_fields():
    adapter = make_adapter()

    result = adapter.normalize_user(
        {
            "id": "EMP003",
            "name": "Employee",
        }
    )

    assert result.user_id == "EMP003"
    assert result.name == "Employee"
    assert result.username is None
    assert result.email is None
    assert result.department is None
    assert result.role is None
    assert result.system_id is None


def test_normalize_system_record():
    adapter = make_adapter()

    result = adapter.normalize_system(
        {
            "id": "SYS001",
            "name": "Central Server",
            "system_number": "001",
        }
    )

    assert result.system_id == "SYS001"
    assert result.name == "Central Server"
    assert result.system_number == "001"
    assert result.active is True


def test_normalize_inactive_system():
    adapter = make_adapter()

    result = adapter.normalize_system(
        {
            "id": "SYS002",
            "name": "Old Server",
            "active": False,
        }
    )

    assert result.system_id == "SYS002"
    assert result.active is False


def test_normalize_system_allows_missing_optional_fields():
    adapter = make_adapter()

    result = adapter.normalize_system(
        {
            "id": "SYS003",
        }
    )

    assert result.system_id == "SYS003"
    assert result.name is None
    assert result.system_number is None


def test_normalize_user_requires_external_id():
    adapter = make_adapter()

    with pytest.raises(ValueError):
        adapter.normalize_user(
            {
                "name": "Employee",
            }
        )


def test_normalize_system_requires_external_id():
    adapter = make_adapter()

    with pytest.raises(ValueError):
        adapter.normalize_system(
            {
                "name": "Server",
            }
        )


def test_normalize_user_rejects_invalid_record():
    adapter = make_adapter()

    with pytest.raises(TypeError):
        adapter.normalize_user("invalid")


def test_normalize_system_rejects_invalid_record():
    adapter = make_adapter()

    with pytest.raises(TypeError):
        adapter.normalize_system("invalid")
