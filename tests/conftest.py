from typing import TypeVar

import pytest
from pydantic import BaseModel

from src.application.agents.base_agent import Expert
from src.application.agents.security_expert.tools import (
    CHECK_DEPENDENCY,
    DETECT_EXPOSED_SECRETS,
    check_dependency,
    detect_exposed_secrets,
)
from src.application.ports.models import Message, ToolDescription

T = TypeVar("T", bound=BaseModel)


class FakeLLM:
    """Scripted stand-in for an LLM in tests: returns the answers a test queued, in order, and records each call."""

    def __init__(self) -> None:
        self.replies: list[Message] = []  # what run returns, one per call
        self.structured_replies: list[BaseModel] = []  # what run_structured returns, one per call
        self.calls: list[dict] = []  # what the code under test sent, for assertions

    async def run(self, messages: list[Message], tools: list[ToolDescription]) -> Message:
        """Return the next queued reply."""
        self.calls.append({"method": "run", "messages": messages, "tools": tools})
        if not self.replies:
            raise AssertionError("FakeLLM.run was called but the test queued no more replies")
        return self.replies.pop(0)

    async def run_structured(self, messages: list[Message], schema: type[T]) -> T:
        """Return the next queued structured reply; it must be an instance of schema."""
        self.calls.append({"method": "run_structured", "messages": messages, "schema": schema})
        if not self.structured_replies:
            raise AssertionError("FakeLLM.run_structured was called but the test queued no more replies")
        reply = self.structured_replies.pop(0)
        if not isinstance(reply, schema):
            raise AssertionError(f"FakeLLM queued a {type(reply).__name__}, but the code asked for a {schema.__name__}")
        return reply


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def expert(fake_llm):
    """A real Expert, talking to the test's fake LLM (the same FakeLLM instance the test receives as fake_llm)."""
    return Expert(
        name="TestExpert",
        sys_message="agent instructions",
        report_sys_message="report instructions",
        llm=fake_llm,
        tool_descriptions=[DETECT_EXPOSED_SECRETS, CHECK_DEPENDENCY],
        tools=[detect_exposed_secrets, check_dependency],
        max_tool_rounds=2,
    )
