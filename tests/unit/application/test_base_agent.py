import pytest

from src.application.agents.models import ExpertReport
from src.application.ports.models import Message, Owner, ToolRequest
from src.domain.models import FindingContent, Severity


@pytest.mark.anyio
async def test_call(expert, fake_llm):
    history = [
        Message(
            id="u1",
            owner=Owner.USER,
            content="diff --git a/app/services/fx.py b/app/services/fx.py\n"
            "+++ b/app/services/fx.py\n"
            '+FX_API_KEY = "fxk_live_123456"\n',  # gitleaks:allow
        )
    ]
    fake_llm.replies.append(Message(id="a1", owner=Owner.ASSISTANT, content="No issues found."))

    response = await expert(history=history)

    # What the expert returned: the model's reply, unchanged
    assert response.owner == Owner.ASSISTANT
    assert response.content == "No issues found."

    # What the expert sent to the LLM
    assert len(fake_llm.calls) == 1
    sent = fake_llm.calls[0]
    assert sent["messages"][0].owner == Owner.SYSTEM
    assert sent["messages"][0].content == "agent instructions"
    assert sent["messages"][1:] == history
    assert [tool.name for tool in sent["tools"]] == ["detect_exposed_secrets", "check_dependency"]

    # The system message was added for this call only
    assert len(history) == 1


def test_run_tools(expert):
    diff = (
        "diff --git a/app/services/fx.py b/app/services/fx.py\n"
        "+++ b/app/services/fx.py\n"
        '+FX_API_KEY = "fxk_live_123456"\n'  # gitleaks:allow
    )

    history = [
        Message(
            id="u1",
            owner=Owner.ASSISTANT,
            content=diff,
            tool_requests=[
                ToolRequest(id="t1", name="detect_exposed_secrets", arguments={"file_path": "app/services/fx.py"}),
                ToolRequest(id="t2", name="check_dependency", arguments={"package": "requests", "version": "2.19.1"}),
                ToolRequest(id="t3", name="no_such_tool", arguments={"package": "requests", "version": "2.19.1"}),
            ],
        )
    ]

    tool_results = expert.run_tools(history=history, diff=diff)

    assert len(tool_results) == 3
    assert tool_results[0].id == "tool-t1"
    assert tool_results[0].owner == Owner.TOOL
    assert tool_results[0].answers_tool_request_id == "t1"
    assert "fxk_live_123456" in tool_results[0].content

    assert tool_results[1].id == "tool-t2"
    assert tool_results[1].owner == Owner.TOOL
    assert tool_results[1].answers_tool_request_id == "t2"
    assert "VULNERABLE" in tool_results[1].content

    assert tool_results[2].id == "tool-t3"
    assert tool_results[2].owner == Owner.TOOL
    assert tool_results[2].answers_tool_request_id == "t3"
    assert tool_results[2].content.startswith("Error: ")


def test_should_continue(expert):
    diff = (
        "diff --git a/app/services/fx.py b/app/services/fx.py\n"
        "+++ b/app/services/fx.py\n"
        '+FX_API_KEY = "fxk_live_123456"\n'  # gitleaks:allow
    )

    history = [
        Message(
            id="u1",
            owner=Owner.ASSISTANT,
            content=diff,
            tool_requests=[
                ToolRequest(id="t1", name="detect_exposed_secrets", arguments={"file_path": "app/services/fx.py"}),
                ToolRequest(id="t2", name="check_dependency", arguments={"package": "requests", "version": "2.19.1"}),
                ToolRequest(id="t3", name="no_such_tool", arguments={"package": "requests", "version": "2.19.1"}),
            ],
        )
    ]

    # Test with tool requests and under threshold
    response = expert.should_continue(history=history, tool_rounds=1)
    assert response

    # Test with tool requests and equal to threshold
    response = expert.should_continue(history=history, tool_rounds=2)
    assert not response

    # Test with tool requests and above threshold
    response = expert.should_continue(history=history, tool_rounds=3)
    assert not response

    # Test without tool requests and under threshold
    history = [Message(id="u1", owner=Owner.ASSISTANT, content=diff, tool_requests=[])]

    # Test without tool requests and under threshold
    response = expert.should_continue(history=history, tool_rounds=1)
    assert not response

    # Test without tool requests and equal to threshold
    response = expert.should_continue(history=history, tool_rounds=2)
    assert not response

    # Test without tool requests and above threshold
    response = expert.should_continue(history=history, tool_rounds=3)
    assert not response


@pytest.mark.anyio
async def test_format_report_with_tool_requests(expert, fake_llm):
    diff = (
        "diff --git a/app/services/fx.py b/app/services/fx.py\n"
        "+++ b/app/services/fx.py\n"
        '+FX_API_KEY = "fxk_live_123456"\n'  # gitleaks:allow
    )

    # The tool budget ran out: the model's last reply still requests two tools nobody ran
    history = [
        Message(id="u1", owner=Owner.USER, content=diff),
        Message(
            id="a1",
            owner=Owner.ASSISTANT,
            content="",
            tool_requests=[
                ToolRequest(id="t1", name="detect_exposed_secrets", arguments={"file_path": "app/services/fx.py"}),
                ToolRequest(id="t2", name="check_dependency", arguments={"package": "requests", "version": "2.19.1"}),
            ],
        ),
    ]

    # The report the LLM will return: format_report calls run_structured, so it goes in structured_replies
    fake_llm.structured_replies.append(
        ExpertReport(
            findings=[
                FindingContent(
                    file="app/services/fx.py",
                    line=1,
                    severity=Severity.CRITICAL,
                    message="Hardcoded API key FX_API_KEY committed in source code.",
                )
            ]
        )
    )

    findings, refusals = await expert.format_report(history=history)

    # Findings
    assert findings[0].id == "TestExpert-0"
    assert findings[0].expert_name == "TestExpert"
    assert [finding.file for finding in findings] == ["app/services/fx.py"]
    assert [finding.line for finding in findings] == [1]
    assert [finding.severity for finding in findings] == [Severity.CRITICAL]
    assert [finding.message for finding in findings] == ["Hardcoded API key FX_API_KEY committed in source code."]

    # Refusals
    assert len(refusals) == 2
    assert [refusal.id for refusal in refusals] == ["tool-t1", "tool-t2"]
    assert [refusal.owner for refusal in refusals] == [Owner.TOOL] * 2
    assert [refusal.content for refusal in refusals] == ["Not executed: tool budget exhausted."] * 2
    assert [refusal.answers_tool_request_id for refusal in refusals] == ["t1", "t2"]

    # What the expert sent to the LLM
    assert len(fake_llm.calls) == 1
    sent = fake_llm.calls[0]
    assert sent["messages"][0].owner == Owner.SYSTEM
    assert sent["messages"][0].content == "report instructions"
    assert sent["messages"][1:] == history + refusals
    assert sent["method"] == "run_structured"
    assert sent["schema"] is ExpertReport


@pytest.mark.anyio
async def test_format_report_without_tool_requests(expert, fake_llm):
    diff = (
        "diff --git a/app/services/fx.py b/app/services/fx.py\n"
        "+++ b/app/services/fx.py\n"
        '+FX_API_KEY = "fxk_live_123456"\n'  # gitleaks:allow
    )

    # The model finished on its own: its last reply requests no tools
    history = [
        Message(id="u1", owner=Owner.USER, content=diff),
        Message(id="a1", owner=Owner.ASSISTANT, content="", tool_requests=[]),
    ]

    # The report the LLM will return: format_report calls run_structured, so it goes in structured_replies
    fake_llm.structured_replies.append(
        ExpertReport(
            findings=[
                FindingContent(
                    file="app/services/fx.py",
                    line=1,
                    severity=Severity.CRITICAL,
                    message="Hardcoded API key FX_API_KEY committed in source code.",
                )
            ]
        )
    )

    findings, refusals = await expert.format_report(history=history)

    # Findings
    assert findings[0].id == "TestExpert-0"
    assert findings[0].expert_name == "TestExpert"
    assert [finding.file for finding in findings] == ["app/services/fx.py"]
    assert [finding.line for finding in findings] == [1]
    assert [finding.severity for finding in findings] == [Severity.CRITICAL]
    assert [finding.message for finding in findings] == ["Hardcoded API key FX_API_KEY committed in source code."]

    # Refusals
    assert refusals == []

    # What the expert sent to the LLM
    assert len(fake_llm.calls) == 1
    sent = fake_llm.calls[0]
    assert sent["messages"][0].owner == Owner.SYSTEM
    assert sent["messages"][0].content == "report instructions"
    assert sent["messages"][1:] == history
    assert sent["method"] == "run_structured"
    assert sent["schema"] is ExpertReport
