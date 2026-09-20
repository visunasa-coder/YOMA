import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class RedactionMode(str, Enum):
    MASK = "MASK"
    REMOVE = "REMOVE"
    TOKENIZE = "TOKENIZE"


@dataclass(frozen=True)
class DataMinimizationResult:
    value: str
    redactions: int
    mode: RedactionMode
    minimized: bool
    requires_human_approval: bool = True
    executable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "redactions": self.redactions,
            "mode": self.mode.value,
            "minimized": self.minimized,
            "requires_human_approval": self.requires_human_approval,
            "executable": self.executable,
        }


class DataMinimizer:
    _patterns = (
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        r"\b(?:\+91[- ]?)?[6-9]\d{9}\b",
        r"(?i)\bpassword\s*[:=]\s*\S+",
        r"(?i)\b(?:api[_-]?key|secret|token)\s*[:=]\s*\S+",
    )

    def minimize(
        self,
        value: str,
        *,
        mode: RedactionMode = RedactionMode.MASK,
    ) -> DataMinimizationResult:
        output = value
        count = 0

        for pattern in self._patterns:
            if mode == RedactionMode.REMOVE:
                replacement = ""
            elif mode == RedactionMode.TOKENIZE:
                replacement = "[REDACTED_TOKEN]"
            else:
                replacement = "[REDACTED]"

            output, replacements = re.subn(pattern, replacement, output)
            count += replacements

        return DataMinimizationResult(
            value=output,
            redactions=count,
            mode=mode,
            minimized=count > 0,
        )
