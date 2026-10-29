"""Domain models of a code review."""

from enum import StrEnum

from pydantic import BaseModel, Field


class Severity(StrEnum):
    """Severity of a finding."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class FindingContent(BaseModel):
    """What is reported about one issue in the code."""

    file: str
    line: int
    severity: Severity
    message: str = Field(description="What is wrong and why it matters")


class Finding(FindingContent):
    """A reported issue, identified and attributed to the expert that found it."""

    id: str
    expert_name: str


class RejectedFinding(BaseModel):
    """A finding that was dropped, with the reason why."""

    finding: Finding
    reason: str


class Review(BaseModel):
    """The findings collected for a pull request."""

    findings: list[Finding]
