"""Explicit Google Workspace provider adapter for YOMA."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any


class IntegrationProviderError(RuntimeError):
    """Base error for provider adapter failures."""


class IntegrationNotImplemented(IntegrationProviderError):
    """Raised when a registered capability has no provider implementation."""


@dataclass(frozen=True)
class IntegrationResult:
    capability_id: str
    items: list[dict[str, Any]]
    metadata: dict[str, Any]


class GoogleWorkspaceAdapter:
    """Explicit Google Workspace adapter.

    Only explicitly registered Google capabilities are implemented.
    This adapter does not expose a generic HTTP client.
    """

    integration_id = "google_workspace"

    GMAIL_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
    GMAIL_MESSAGE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"

    CALENDAR_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    CONTACTS_URL = "https://people.googleapis.com/v1/people/me/connections"
    DRIVE_URL = "https://www.googleapis.com/drive/v3/files"
    DRIVE_FILE_URL = "https://www.googleapis.com/drive/v3/files/{file_id}"

    def _request(
        self,
        *,
        url: str,
        access_token: str,
        query: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not access_token:
            raise IntegrationProviderError("access token is unavailable")

        if query:
            url = f"{url}?{urlencode(query, doseq=True)}"

        request = Request(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=20.0) as response:
                raw = response.read()
        except HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode("utf-8"))
            except Exception:
                detail = {}

            message = None
            if isinstance(detail, dict):
                error = detail.get("error")
                if isinstance(error, dict):
                    message = error.get("message")
                elif isinstance(error, str):
                    message = error

            raise IntegrationProviderError(
                f"Google API request failed: {exc.code}"
                + (f": {message}" if message else "")
            ) from exc
        except URLError as exc:
            raise IntegrationProviderError(
                "Google API endpoint is unreachable"
            ) from exc

        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IntegrationProviderError(
                "Google API returned invalid JSON"
            ) from exc

        if not isinstance(data, dict):
            raise IntegrationProviderError(
                "Google API returned an invalid response"
            )

        return data

    @staticmethod
    def _json_request(
        self,
        *,
        url: str,
        access_token: str,
        payload: dict[str, Any],
        method: str = "POST",
    ) -> dict[str, Any]:
        if not access_token:
            raise IntegrationProviderError("access token is unavailable")

        body = json.dumps(payload).encode("utf-8")

        request = Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method=method,
        )

        try:
            with urlopen(request, timeout=20.0) as response:
                raw = response.read()
        except HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode("utf-8"))
            except Exception:
                detail = {}

            message = None
            if isinstance(detail, dict):
                error = detail.get("error")
                if isinstance(error, dict):
                    message = error.get("message")
                elif isinstance(error, str):
                    message = error

            raise IntegrationProviderError(
                f"Google API request failed: {exc.code}"
                + (f": {message}" if message else "")
            ) from exc
        except URLError as exc:
            raise IntegrationProviderError(
                "Google API endpoint is unreachable"
            ) from exc

        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IntegrationProviderError(
                "Google API returned invalid JSON"
            ) from exc

        if not isinstance(data, dict):
            raise IntegrationProviderError(
                "Google API returned an invalid response"
            )

        return data

    def _bounded_max_results(self, max_results: int) -> int:
        if isinstance(max_results, bool):
            raise IntegrationProviderError("max_results must be an integer")

        if not isinstance(max_results, int):
            raise IntegrationProviderError("max_results must be an integer")

        if max_results < 1:
            raise IntegrationProviderError("max_results must be positive")

        return min(max_results, 50)

    def execute(
        self,
        capability_id: str,
        *,
        access_token: str,
        arguments: dict[str, Any],
        max_results: int,
    ) -> IntegrationResult:
        if not access_token:
            raise IntegrationProviderError("access token is unavailable")

        bounded = self._bounded_max_results(max_results)

        if capability_id == "google.gmail.read":
            return self.gmail_read(
                access_token=access_token,
                arguments=arguments,
                max_results=bounded,
            )

        if capability_id == "google.calendar.read":
            return self.calendar_read(
                access_token=access_token,
                arguments=arguments,
                max_results=bounded,
            )

        if capability_id == "google.contacts.read":
            return self.contacts_read(
                access_token=access_token,
                arguments=arguments,
                max_results=bounded,
            )

        if capability_id == "google.drive.read":
            return self.drive_read(
                access_token=access_token,
                arguments=arguments,
                max_results=bounded,
            )

        if capability_id == "google.gmail.send":
            return self.gmail_send(
                access_token=access_token,
                arguments=arguments,
            )

        if capability_id == "google.calendar.create":
            return self.calendar_create(
                access_token=access_token,
                arguments=arguments,
            )

        raise IntegrationNotImplemented(
            f"unsupported Google Workspace capability: {capability_id}"
        )

    def gmail_read(
        self,
        *,
        access_token: str,
        arguments: dict[str, Any],
        max_results: int,
    ) -> IntegrationResult:
        query: dict[str, Any] = {
            "maxResults": max_results,
        }

        search_query = arguments.get("query")
        if search_query is not None:
            if not isinstance(search_query, str):
                raise IntegrationProviderError(
                    "Gmail query must be a string"
                )
            if search_query:
                query["q"] = search_query

        data = self._request(
            url=self.GMAIL_URL,
            access_token=access_token,
            query=query,
        )

        messages = data.get("messages", [])
        if not isinstance(messages, list):
            messages = []

        items: list[dict[str, Any]] = []

        for message in messages[:max_results]:
            if not isinstance(message, dict):
                continue

            message_id = message.get("id")
            if not isinstance(message_id, str) or not message_id:
                continue

            detail = self._request(
                url=self.GMAIL_MESSAGE_URL.format(message_id=message_id),
                access_token=access_token,
                query={
                    "format": "metadata",
                    "metadataHeaders": [
                        "From",
                        "To",
                        "Subject",
                        "Date",
                    ],
                },
            )

            items.append(
                {
                    "id": message_id,
                    "thread_id": detail.get("threadId"),
                    "label_ids": detail.get("labelIds", []),
                    "snippet": detail.get("snippet", ""),
                    "internal_date": detail.get("internalDate"),
                    "payload": detail.get("payload", {}),
                }
            )

        return IntegrationResult(
            capability_id="google.gmail.read",
            items=items,
            metadata={
                "provider": self.integration_id,
                "count": len(items),
                "max_results": max_results,
                "next_page_token": data.get("nextPageToken"),
            },
        )

    def calendar_read(
        self,
        *,
        access_token: str,
        arguments: dict[str, Any],
        max_results: int,
    ) -> IntegrationResult:
        query: dict[str, Any] = {
            "maxResults": max_results,
            "singleEvents": "true",
            "orderBy": "startTime",
        }

        for key in ("timeMin", "timeMax", "pageToken"):
            value = arguments.get(key)
            if value is not None:
                if not isinstance(value, str):
                    raise IntegrationProviderError(
                        f"Calendar {key} must be a string"
                    )
                query[key] = value

        data = self._request(
            url=self.CALENDAR_URL,
            access_token=access_token,
            query=query,
        )

        events = data.get("items", [])
        if not isinstance(events, list):
            events = []

        items = [
            event
            for event in events[:max_results]
            if isinstance(event, dict)
        ]

        return IntegrationResult(
            capability_id="google.calendar.read",
            items=items,
            metadata={
                "provider": self.integration_id,
                "count": len(items),
                "max_results": max_results,
                "next_page_token": data.get("nextPageToken"),
            },
        )


    def gmail_send(
        self,
        *,
        access_token: str,
        arguments: dict[str, Any],
    ) -> IntegrationResult:
        import base64
        from email.message import EmailMessage

        to = arguments.get("to")
        subject = arguments.get("subject", "")
        body = arguments.get("body", "")

        if not isinstance(to, str) or not to.strip():
            raise IntegrationProviderError("Gmail recipient is required")

        if not isinstance(subject, str):
            raise IntegrationProviderError("Gmail subject must be a string")

        if not isinstance(body, str):
            raise IntegrationProviderError("Gmail body must be a string")

        message = EmailMessage()
        message["To"] = to.strip()
        message["Subject"] = subject
        message.set_content(body)

        encoded = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode("ascii")

        result = self._json_request(
            url="https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            access_token=access_token,
            payload={"raw": encoded},
        )

        return IntegrationResult(
            capability_id="google.gmail.send",
            items=[result],
            metadata={
                "provider": self.integration_id,
                "executed": True,
            },
        )

    def calendar_create(
        self,
        *,
        access_token: str,
        arguments: dict[str, Any],
    ) -> IntegrationResult:
        summary = arguments.get("summary")
        start = arguments.get("start")
        end = arguments.get("end")

        if not isinstance(summary, str) or not summary.strip():
            raise IntegrationProviderError("Calendar summary is required")

        if not isinstance(start, dict):
            raise IntegrationProviderError("Calendar start is required")

        if not isinstance(end, dict):
            raise IntegrationProviderError("Calendar end is required")

        event = {
            "summary": summary.strip(),
            "start": start,
            "end": end,
        }

        for key in ("description", "location", "attendees", "reminders"):
            if key in arguments:
                event[key] = arguments[key]

        calendar_id = arguments.get("calendar_id", "primary")

        if not isinstance(calendar_id, str) or not calendar_id:
            raise IntegrationProviderError("Calendar ID is invalid")

        result = self._json_request(
            url=(
                "https://www.googleapis.com/calendar/v3/calendars/"
                + calendar_id
                + "/events"
            ),
            access_token=access_token,
            payload=event,
        )

        return IntegrationResult(
            capability_id="google.calendar.create",
            items=[result],
            metadata={
                "provider": self.integration_id,
                "executed": True,
            },
        )

    def drive_read(
        self,
        *,
        access_token: str,
        arguments: dict[str, Any],
        max_results: int,
    ) -> IntegrationResult:
        query: dict[str, Any] = {
            "pageSize": max_results,
            "fields": (
                "nextPageToken,"
                "files(id,name,mimeType,size,modifiedTime,"
                "webViewLink,parents)"
            ),
        }

        search_query = arguments.get("query")

        if search_query is not None:
            if not isinstance(search_query, str):
                raise IntegrationProviderError(
                    "Drive query must be a string"
                )
            if search_query:
                query["q"] = search_query

        page_token = arguments.get("pageToken")

        if page_token is not None:
            if not isinstance(page_token, str):
                raise IntegrationProviderError(
                    "Drive pageToken must be a string"
                )
            query["pageToken"] = page_token

        data = self._request(
            url=self.DRIVE_URL,
            access_token=access_token,
            query=query,
        )

        files = data.get("files", [])

        if not isinstance(files, list):
            files = []

        items = [
            item
            for item in files[:max_results]
            if isinstance(item, dict)
        ]

        return IntegrationResult(
            capability_id="google.drive.read",
            items=items,
            metadata={
                "provider": self.integration_id,
                "count": len(items),
                "max_results": max_results,
                "next_page_token": data.get("nextPageToken"),
            },
        )

    def contacts_read(
        self,
        *,
        access_token: str,
        arguments: dict[str, Any],
        max_results: int,
    ) -> IntegrationResult:
        query: dict[str, Any] = {
            "pageSize": max_results,
            "personFields": "names,emailAddresses,phoneNumbers,organizations",
        }

        page_token = arguments.get("pageToken")
        if page_token is not None:
            if not isinstance(page_token, str):
                raise IntegrationProviderError(
                    "Contacts pageToken must be a string"
                )
            query["pageToken"] = page_token

        data = self._request(
            url=self.CONTACTS_URL,
            access_token=access_token,
            query=query,
        )

        connections = data.get("connections", [])
        if not isinstance(connections, list):
            connections = []

        items = [
            contact
            for contact in connections[:max_results]
            if isinstance(contact, dict)
        ]

        return IntegrationResult(
            capability_id="google.contacts.read",
            items=items,
            metadata={
                "provider": self.integration_id,
                "count": len(items),
                "max_results": max_results,
                "next_page_token": data.get("nextPageToken"),
            },
        )
