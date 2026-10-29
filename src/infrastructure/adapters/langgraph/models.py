"""State types of the LangGraph review graph."""

import operator
from typing import Annotated, TypedDict

from src.domain.models import Finding


class ReviewState(TypedDict):
    """The state shared by the nodes of the review graph; reducer keys add up the writes of parallel nodes."""

    pr_url: str
    diff: str
    findings: Annotated[list[Finding], operator.add]
    summary: str
    context_attempts: Annotated[int, operator.add]
