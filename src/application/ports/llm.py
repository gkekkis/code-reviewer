"""Port for the LLM used by the agents."""

from typing import Protocol, TypeVar

from pydantic import BaseModel

from src.application.ports.models import Message, ToolDescription

T = TypeVar("T", bound=BaseModel)


class LLMPort(Protocol):
    """Interface an LLM client must implement."""

    async def run(self, messages: list[Message], tools: list[ToolDescription]) -> Message:
        """Return the completion for the given messages."""
        ...

    async def run_structured(self, messages: list[Message], schema: type[T]) -> T:
        """Send the conversation; return the answer as an instance of schema."""
        ...
