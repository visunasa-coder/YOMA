import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class SensitiveDataType(str, Enum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    CARD_NUMBER = "CARD_NUMBER"
    SECRET = "SECRET"
    API_KEY = "API_KEY"
    PASSWORD = "PASSWORD"
    GOVERNMENT_ID = "GOVERNMENT_ID"


@dataclass(frozen=True)
class SensitiveFinding:
    kind: SensitiveDataType
    start: int
    end: int
    severity: str = "HIGH"

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": self.kind.value,
            "start": self.start,
            "end": self.end,
            "severity": self.severity,
        }


class SensitiveDataDetector:
    _patterns = {
        SensitiveDataType.EMAIL: r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        SensitiveDataType.PHONE: r"\b(?:\+91[- ]?)?[6-9]\d{9}\b",
        SensitiveDataType.BANK_ACCOUNT: r"\b\d{9,18}\b",
        SensitiveDataType.CARD_NUMBER: r"\b(?:\d[ -]?){13,19}\b",
        SensitiveDataType.API_KEY: r"\b(?:sk-|AIza|ghp_)[A-Za-z0-9_-]{12,}\b",
        SensitiveDataType.PASSWORD: r"(?i)\bpassword\s*[:=]\s*\S+",
        SensitiveDataType.SECRET: r"(?i)\bsecret\s*[:=]\s*\S+",
        SensitiveDataType.GOVERNMENT_ID: r"\b[A-Z]{5}\d{4}[A-Z]\b",
    }

    def scan(self, text: str) -> tuple[SensitiveFinding, ...]:
        findings = []

        for kind, pattern in self._patterns.items():
            for match in re.finditer(pattern, text):
                findings.append(
                    SensitiveFinding(
                        kind=kind,
                        start=match.start(),
                        end=match.end(),
                    )
                )

        return tuple(
            sorted(findings, key=lambda item: (item.start, item.end))
        )
