"""Answer schemas the experts ask the LLM to fill."""

from pydantic import BaseModel

from src.domain.models import FindingContent


class ExpertReport(BaseModel):
    """The findings an expert reports at the end of its review."""

    findings: list[FindingContent]
