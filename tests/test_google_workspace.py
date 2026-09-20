from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import patch

from yoma.google_workspace import (
    GoogleWorkspaceAdapter,
    IntegrationNotImplemented,
    IntegrationProviderError,
)


def fake_response(payload: dict) -> BytesIO:
    response = BytesIO(json.dumps(payload).encode("utf-8"))
    response.__enter__ = lambda: response
    response.__exit__ = lambda *args: None
    return response


def test_gmail_read() -> None:
    adapter = GoogleWorkspaceAdapter()

    responses = [
        {
            "messages": [
                {"id": "msg-1", "threadId": "thread-1"},
                {"id": "msg-2", "threadId": "thread-2"},
            ]
        },
        {
            "id": "msg-1",
            "threadId": "thread-1",
            "labelIds": ["INBOX"],
            "snippet": "Hello",
            "internalDate": "123456789",
            "payload": {"headers": []},
        },
        {
            "id": "msg-2",
            "threadId": "thread-2",
            "labelIds": ["SENT"],
            "snippet": "World",
            "internalDate": "123456790",
            "payload": {"headers": []},
        },
    ]

    with patch(
        "yoma.google_workspace.urlopen",
        side_effect=[fake_response(item) for item in responses],
    ):
        result = adapter.gmail_read(
            access_token="test-token",
            arguments={"query": "from:test@example.com"},
            max_results=2,
        )

    assert result.capability_id == "google.gmail.read"
    assert len(result.items) == 2
    assert result.items[0]["id"] == "msg-1"
    assert result.items[1]["id"] == "msg-2"
    assert result.metadata["count"] == 2


def test_calendar_read() -> None:
    adapter = GoogleWorkspaceAdapter()

    payload = {
        "items": [
            {"id": "event-1", "summary": "Meeting"},
            {"id": "event-2", "summary": "Review"},
        ],
        "nextPageToken": "next-page",
    }

    with patch(
        "yoma.google_workspace.urlopen",
        return_value=fake_response(payload),
    ):
        result = adapter.calendar_read(
            access_token="test-token",
            arguments={},
            max_results=2,
        )

    assert result.capability_id == "google.calendar.read"
    assert len(result.items) == 2
    assert result.items[0]["id"] == "event-1"
    assert result.metadata["next_page_token"] == "next-page"


def test_contacts_read() -> None:
    adapter = GoogleWorkspaceAdapter()

    payload = {
        "connections": [
            {
                "resourceName": "people/c123",
                "names": [{"displayName": "Alice"}],
                "emailAddresses": [{"value": "alice@example.com"}],
            }
        ]
    }

    with patch(
        "yoma.google_workspace.urlopen",
        return_value=fake_response(payload),
    ):
        result = adapter.contacts_read(
            access_token="test-token",
            arguments={},
            max_results=10,
        )

    assert result.capability_id == "google.contacts.read"
    assert len(result.items) == 1
    assert result.items[0]["resourceName"] == "people/c123"


def test_max_results_is_bounded_to_50() -> None:
    adapter = GoogleWorkspaceAdapter()

    assert adapter._bounded_max_results(100) == 50
    assert adapter._bounded_max_results(50) == 50
    assert adapter._bounded_max_results(10) == 10


def test_invalid_max_results_is_rejected() -> None:
    adapter = GoogleWorkspaceAdapter()

    for value in (0, -1, True, "10"):
        try:
            adapter._bounded_max_results(value)
        except IntegrationProviderError:
            pass
        else:
            raise AssertionError(f"{value!r} should have been rejected")


def test_missing_access_token_is_rejected() -> None:
    adapter = GoogleWorkspaceAdapter()

    try:
        adapter.execute(
            "google.gmail.read",
            access_token="",
            arguments={},
            max_results=10,
        )
    except IntegrationProviderError as exc:
        assert "access token" in str(exc).lower()
    else:
        raise AssertionError("missing access token should fail")


def test_unknown_capability_is_rejected() -> None:
    adapter = GoogleWorkspaceAdapter()

    try:
        adapter.execute(
            "google.unknown.read",
            access_token="test-token",
            arguments={},
            max_results=10,
        )
    except IntegrationNotImplemented:
        pass
    else:
        raise AssertionError("unknown capability should fail")
