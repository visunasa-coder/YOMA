from __future__ import annotations

from ..models.dlp import DLPDecision, FileTransferEvent


class DLPEngine:
    """
    YOMA Data Loss Prevention decision engine.

    The engine evaluates company-controlled transfer events
    against explicit organizational policy.

    It does not autonomously inspect unrelated personal data.
    """

    VALID_ACTIONS = {"allow", "alert", "block"}

    def __init__(
        self,
        *,
        protected_classifications: set[str] | None = None,
        approved_destinations: set[str] | None = None,
        blocked_destinations: set[str] | None = None,
    ) -> None:

        self.protected_classifications = (
            protected_classifications
            if protected_classifications is not None
            else {"confidential", "restricted"}
        )

        self.approved_destinations = (
            approved_destinations
            if approved_destinations is not None
            else set()
        )

        self.blocked_destinations = (
            blocked_destinations
            if blocked_destinations is not None
            else set()
        )

    def evaluate(
        self,
        event: FileTransferEvent,
    ) -> DLPDecision:

        destination = event.destination.strip()

        classification = event.classification.lower().strip()

        if not destination:
            return self._decision(
                event,
                "block",
                "high",
                "Transfer destination is missing.",
            )

        if destination in self.blocked_destinations:
            return self._decision(
                event,
                "block",
                "high",
                "Destination is explicitly blocked by policy.",
            )

        if destination in self.approved_destinations:
            return self._decision(
                event,
                "allow",
                "low",
                "Destination is approved by organization policy.",
            )

        if (
            classification in self.protected_classifications
            and event.device_type == "removable"
        ):
            return self._decision(
                event,
                "block",
                "high",
                "Protected company data cannot be transferred "
                "to an unauthorized removable device.",
            )

        if classification in self.protected_classifications:
            return self._decision(
                event,
                "alert",
                "medium",
                "Protected company data is being transferred "
                "to a destination requiring review.",
            )

        if event.device_type == "removable":
            return self._decision(
                event,
                "alert",
                "medium",
                "Transfer to an unapproved removable device "
                "requires review.",
            )

        return self._decision(
            event,
            "allow",
            "low",
            "Transfer does not violate the configured policy.",
        )

    def _decision(
        self,
        event: FileTransferEvent,
        action: str,
        risk: str,
        reason: str,
    ) -> DLPDecision:

        if action not in self.VALID_ACTIONS:
            raise ValueError(f"Invalid DLP action: {action}")

        return DLPDecision(
            action=action,
            risk=risk,
            reason=reason,
            alert_required=action == "alert",
            block_required=action == "block",
            employee_id=event.employee_id,
            destination=event.destination,
            classification=event.classification,
        )
