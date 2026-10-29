"""Types the application uses to talk to an LLM, independent of any LLM library."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class Owner(StrEnum):
    """Who a message comes from."""

    SYSTEM = "system"
    USER = "user"
    TOOL = "tool"
    ASSISTANT = "assistant"


class ToolRequest(BaseModel):
    """One tool the model asks to run, with the arguments it chose."""

    id: str
    name: str
    arguments: dict[str, Any]


class ToolDescription(BaseModel):
    """A tool as the model sees it: its name, what it does, and the arguments it takes."""

    name: str
    description: str
    arguments: type[BaseModel]


class Message(BaseModel):
    """One message of the conversation with the LLM."""

    id: str
    owner: Owner
    content: str
    tool_requests: list[ToolRequest] = []  # assistant messages: the tools the model asks to run
    answers_tool_request_id: str | None = None  # tool messages: the id of the ToolRequest this answers
