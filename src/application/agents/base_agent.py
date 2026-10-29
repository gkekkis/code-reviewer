"""The expert agent shared by all reviewers: one class, configured per expert with its prompts, tools and limits."""

import inspect
from collections.abc import Callable

from src.application.agents.models import ExpertReport
from src.application.ports.llm import LLMPort
from src.application.ports.models import Message, Owner, ToolDescription
from src.domain.models import Finding


class Expert:
    """
    A code-review expert that works in steps: ask the LLM, run the tools it requests, then write a report.

    The class holds only configuration, never data of a single review: one instance serves every review.
    Everything that belongs to one review (the history, the diff, the tool rounds used) is passed into each step.
    """

    def __init__(
        self,
        name: str,
        sys_message: str,
        report_sys_message: str,
        llm: LLMPort,
        tool_descriptions: list[ToolDescription],
        tools: list[Callable],
        max_tool_rounds: int,
    ):
        """
        Store the expert's configuration.

        Args:
            name: Expert name, stamped on every finding it reports.
            sys_message: Instructions for the agent turns: role, scope, how to use the tools.
            report_sys_message: Instructions for the final report.
            llm: The LLM to talk to, through the port, so a real adapter or a fake in tests.
            tool_descriptions: The tools as the model sees them; offered on every agent turn.
            tools: The functions that run the tools; each one's __name__ must match its description's name.
            max_tool_rounds: How many rounds of tool calls the expert may run before it must report.

        """
        self._name = name
        self._sys_message = sys_message
        self._report_sys_message = report_sys_message
        self._llm = llm
        self._tool_descriptions = tool_descriptions
        # Look tools up by name: a ToolRequest from the model names the tool it wants
        self._tool_by_name = {tool.__name__: tool for tool in tools}
        self._max_tool_rounds = max_tool_rounds

    async def __call__(self, history: list[Message]) -> Message:
        """
        Agent turn: look at the conversation so far and either ask for tools or finish.

        Args:
            history: The conversation of this review so far, starting with the user message with the diff.

        Returns:
            The model's reply; its tool_requests are filled when it wants tools.

        """
        # The instructions are added for this call only, never stored in the history
        system_message = Message(id=f"{self._name}-system", owner=Owner.SYSTEM, content=self._sys_message)
        return await self._llm.run(messages=[system_message] + history, tools=self._tool_descriptions)

    def run_tools(self, history: list[Message], diff: str) -> list[Message]:
        """
        Run the tools requested in the last message, injecting the diff where a tool takes it.

        Args:
            history: The conversation so far; its last message holds the tool requests.
            diff: The diff of this review, passed to every tool that has a diff parameter.

        Returns:
            One tool message per request, each linked to its request by answers_tool_request_id.

        """
        last_message = history[-1]
        messages = []

        for request in last_message.tool_requests:
            try:
                tool = self._tool_by_name[request.name]
                args = dict(**request.arguments)

                # The model never chooses the diff (it isn't in any tool's arguments schema); the expert adds it
                if "diff" in inspect.signature(tool).parameters:
                    args["diff"] = diff
                result = tool(**args)
            except Exception as e:
                # Every request must get an answer, so a failure becomes an error message the model can read
                result = f"Error: {e}"

            messages.append(
                Message(
                    id=f"tool-{request.id}", owner=Owner.TOOL, content=str(result), answers_tool_request_id=request.id
                )
            )

        return messages

    def should_continue(self, history: list[Message], tool_rounds: int) -> bool:
        """
        Decide whether to run tools again or write the report.

        Args:
            history: The conversation so far; its last message is the model's latest reply.
            tool_rounds: How many rounds of tool calls this review has already run.

        Returns:
            True to run the requested tools, False to write the report.

        """
        last_message = history[-1]
        return bool(tool_rounds < self._max_tool_rounds and last_message.tool_requests)

    async def format_report(self, history: list[Message]) -> tuple[list[Finding], list[Message]]:
        """
        Turn the conversation into typed findings, stamped with this expert's name.

        Args:
            history: The conversation so far, including the tool results.

        Returns:
            The findings, and the refusal messages that answer any tool requests left unrun. The caller adds the
            refusals to the history so it stays valid for any later LLM call.

        """
        last_message = history[-1]
        refusals = []
        # If the tool budget stopped the loop, the last message has requests nobody answered. The API rejects a
        # conversation with unanswered requests, so each one gets a "not executed" answer
        if last_message.tool_requests:
            refusals = [
                Message(
                    id=f"tool-{request.id}",
                    owner=Owner.TOOL,
                    content="Not executed: tool budget exhausted.",
                    answers_tool_request_id=request.id,
                )
                for request in last_message.tool_requests
            ]

            history = history + refusals

        system_message = Message(id=f"{self._name}-system", owner=Owner.SYSTEM, content=self._report_sys_message)

        report = await self._llm.run_structured(messages=[system_message] + history, schema=ExpertReport)

        # The model fills only the content of each finding; the expert adds the id and its own name
        findings = []
        for i, llm_finding in enumerate(report.findings):
            findings.append(Finding(**llm_finding.model_dump(), id=f"{self._name}-{i}", expert_name=self._name))

        return (findings, refusals)
