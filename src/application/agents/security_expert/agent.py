"""The Security Expert: an Expert configured to review a diff for security issues."""

from collections.abc import Callable

from src.application.agents.base_agent import Expert
from src.application.ports.llm import LLMPort
from src.application.ports.models import ToolDescription


def get_security_expert(
    name: str,
    sys_message: str,
    report_sys_message: str,
    llm: LLMPort,
    tool_descriptions: list[ToolDescription],
    tools: list[Callable],
    max_tool_rounds: int,
) -> Expert:
    """
    Build the Security Expert.

    Args:
        name: Expert name, stamped on every finding it reports.
        sys_message: Instructions for the agent turns: role, scope, how to use the tools.
        report_sys_message: Instructions for the final report.
        llm: The LLM to talk to, through the port.
        tool_descriptions: The tools as the model sees them.
        tools: The functions that run the tools; each one's __name__ must match its description's name.
        max_tool_rounds: How many rounds of tool calls the expert may run before it must report.

    Returns:
        An Expert configured with the given values.

    """
    return Expert(
        name=name,
        sys_message=sys_message,
        report_sys_message=report_sys_message,
        llm=llm,
        tool_descriptions=tool_descriptions,
        tools=tools,
        max_tool_rounds=max_tool_rounds,
    )
