"""M53 first-run setup service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .provisioning import (
    FirstRunSetupWizard,
    GoogleProvisioningManager,
    OAuthJsonValidator,
    ProvisioningStatus,
    SecureProvisioningStore,
)


class YomaSetupService:
    def __init__(self, root: str | Path | None = None):
        self.store = SecureProvisioningStore(root)
        self.google = GoogleProvisioningManager(self.store)

    def welcome(self) -> dict[str, Any]:
        return FirstRunSetupWizard.welcome()

    def instructions(self) -> list[str]:
        return FirstRunSetupWizard.instructions()

    def validate_google_json(self, path: str | Path) -> dict[str, Any]:
        return OAuthJsonValidator.validate_file(path).as_dict()

    def import_google_json(self, path: str | Path) -> dict[str, Any]:
        result = self.google.import_oauth_json(path)

        return {
            "success": result.valid,
            "validation": result.as_dict(),
            "status": self.status().as_dict(),
        }

    def begin_google_authorization(self) -> bool:
        return self.google.begin_authorization()

    def mark_google_authorized(self) -> bool:
        return self.google.mark_authorized()

    def mark_google_connection_test(
        self,
        success: bool,
    ) -> bool:
        return self.google.mark_connection_tested(success)

    def status(self) -> ProvisioningStatus:
        return self.google.status()

    def execution_authorized(self) -> bool:
        return False

    def executable(self) -> bool:
        return False

    def requires_human_approval(self) -> bool:
        return True
