import pytest

from src.application.ports.models import Message, Owner, ToolRequest


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
