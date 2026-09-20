from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class DataClassification(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class DataSensitivity(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DataSubject(str, Enum):
    GENERAL = "GENERAL"
    EMPLOYEE = "EMPLOYEE"
    CUSTOMER = "CUSTOMER"
    FINANCE = "FINANCE"
    SECURITY = "SECURITY"
    CREDENTIAL = "CREDENTIAL"


@dataclass(frozen=True)
class DataClassificationResult:
    classification: DataClassification
    sensitivity: DataSensitivity
    subject: DataSubject
    reason: str
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification.value,
            "sensitivity": self.sensitivity.value,
            "subject": self.subject.value,
            "reason": self.reason,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class DataClassificationEngine:
    _restricted = (
        "password", "passwd", "secret", "api_key", "apikey",
        "private_key", "access_token", "refresh_token",
        "bank_account", "card_number", "cvv", "aadhaar",
        "pan_number", "medical_record",
    )

    _confidential = (
        "salary", "payroll", "employee", "customer",
        "invoice", "contract", "internal", "financial",
    )

    def classify(
        self,
        data: Any,
        *,
        declared: DataClassification | None = None,
        subject: DataSubject = DataSubject.GENERAL,
    ) -> DataClassificationResult:
        text = str(data).lower()

        if declared is not None:
            classification = DataClassification(declared)
        elif any(token in text for token in self._restricted):
            classification = DataClassification.RESTRICTED
        elif any(token in text for token in self._confidential):
            classification = DataClassification.CONFIDENTIAL
        else:
            classification = DataClassification.INTERNAL

        sensitivity = {
            DataClassification.PUBLIC: DataSensitivity.NONE,
            DataClassification.INTERNAL: DataSensitivity.LOW,
            DataClassification.CONFIDENTIAL: DataSensitivity.HIGH,
            DataClassification.RESTRICTED: DataSensitivity.CRITICAL,
        }[classification]

        return DataClassificationResult(
            classification=classification,
            sensitivity=sensitivity,
            subject=subject,
            reason=f"classified as {classification.value}",
        )
