"""Vendor-neutral integration and capability registry with no generic HTTP client."""

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class CapabilityDefinition:
    capability_id: str
    description: str
    required_scope: str
    is_write: bool
    approval_required: bool
    max_results: int


@dataclass(frozen=True)
class IntegrationDefinition:
    integration_id: str
    display_name: str
    description: str
    authentication_method: str
    capabilities: tuple[CapabilityDefinition, ...]
    allowed_hosts: tuple[str, ...]


GOOGLE_CAPABILITIES = (
    CapabilityDefinition("google.gmail.read", "Search bounded Gmail message metadata.", "https://www.googleapis.com/auth/gmail.readonly", False, False, 50),
    CapabilityDefinition("google.gmail.send", "Send Gmail messages only through governed human approval.", "https://www.googleapis.com/auth/gmail.send", True, True, 1),
    CapabilityDefinition("google.calendar.read", "List bounded calendar events.", "https://www.googleapis.com/auth/calendar.readonly", False, False, 50),
    CapabilityDefinition("google.calendar.create", "Create calendar events only through governed human approval.", "https://www.googleapis.com/auth/calendar.events", True, True, 1),
    CapabilityDefinition("google.contacts.read", "List bounded contacts.", "https://www.googleapis.com/auth/contacts.readonly", False, False, 50),
    CapabilityDefinition("google.drive.read", "List bounded Google Drive files.", "https://www.googleapis.com/auth/drive.readonly", False, False, 50),
)

REGISTRY = {
    "google_workspace": IntegrationDefinition(
        "google_workspace", "Google Workspace", "Controlled Google Workspace capabilities with governed write actions.",
        "oauth2_authorization_code", GOOGLE_CAPABILITIES, ("www.googleapis.com", "accounts.google.com"),
    ),
}


def get_integration(integration_id: str) -> IntegrationDefinition | None:
    return REGISTRY.get(integration_id)


def get_capability(integration_id: str, capability_id: str) -> CapabilityDefinition | None:
    integration = get_integration(integration_id)
    if integration is None:
        return None
    return next((capability for capability in integration.capabilities if capability.capability_id == capability_id), None)


def validate_registered_url(integration_id: str, url: str) -> bool:
    integration = get_integration(integration_id)
    if integration is None:
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in integration.allowed_hosts and not parsed.username and not parsed.password
