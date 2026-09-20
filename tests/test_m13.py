from yoma.google_workspace import (
    GoogleWorkspaceAdapter,
    IntegrationNotImplemented,
)


def test_google_workspace_adapter_rejects_unknown_capability():
    adapter = GoogleWorkspaceAdapter()

    try:
        adapter.execute(
            "google.unknown",
            access_token="test-token",
            arguments={},
            max_results=10,
        )
    except IntegrationNotImplemented:
        pass
    else:
        raise AssertionError("unknown capability was accepted")


def test_google_workspace_adapter_requires_token():
    adapter = GoogleWorkspaceAdapter()

    try:
        adapter.execute(
            "google.gmail.read",
            access_token="",
            arguments={},
            max_results=10,
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("missing access token was accepted")


def test_google_workspace_adapter_has_explicit_capabilities():
    adapter = GoogleWorkspaceAdapter()

    assert adapter.integration_id == "google_workspace"
    assert callable(adapter.gmail_read)
    assert callable(adapter.calendar_read)
    assert callable(adapter.contacts_read)
