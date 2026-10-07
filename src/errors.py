"""Clear, specific exceptions and the shared validation Issue type."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    location: str = ""
    severity: Severity = Severity.ERROR

    def __str__(self) -> str:
        return f"[{self.severity.value}] {self.code} @ {self.location or '-'}: {self.message}"


class ResearchMapError(Exception):
    """Base class for all ResearchMap errors."""


class ConfigError(ResearchMapError):
    """Configuration file is missing or invalid."""


class OntologyError(ResearchMapError):
    """The ontology specification is invalid. The build must not continue."""

    def __init__(self, problems: Sequence[str]):
        self.problems = list(problems)
        super().__init__("Invalid ontology specification:\n  - " + "\n  - ".join(self.problems))


class KnowledgeStateCorruptError(ResearchMapError):
    """A knowledge-state file is unreadable or structurally malformed."""


class ValidationFailed(ResearchMapError):
    """One or more ERROR-level issues were found. Nothing is silently repaired."""

    def __init__(self, issues: Sequence[Issue]):
        self.issues = list(issues)
        errs = [i for i in self.issues if i.severity == Severity.ERROR]
        super().__init__(f"{len(errs)} validation error(s):\n  " + "\n  ".join(str(i) for i in errs))


class SealMismatchError(ResearchMapError):
    """A sealed file's hash does not match its committed seal."""
