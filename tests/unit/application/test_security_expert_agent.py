import pytest

from src.application.agents.base_agent import Expert
from src.application.agents.models import ExpertReport
from src.application.agents.security_expert.agent import get_security_expert
from src.application.agents.security_expert.tools import (
    CHECK_DEPENDENCY,
    DETECT_EXPOSED_SECRETS,
    check_dependency,
    detect_exposed_secrets,
)
from src.application.ports.models import Message, Owner, ToolRequest
from src.domain.models import FindingContent, Severity


@pytest.mark.anyio
async def test_security_expert_creation(fake_llm):
    security_expert = get_security_expert(
        name="SecurityExpert",
        sys_message="Security Expert system message",
        report_sys_message="Security Expert report system message",
        llm=fake_llm,
        tool_descriptions=[DETECT_EXPOSED_SECRETS, CHECK_DEPENDENCY],
        tools=[check_dependency, detect_exposed_secrets],
        max_tool_rounds=3,
    )

    assert isinstance(security_expert, Expert)

    # sys_message and tool_descriptions: what an agent turn sends to the LLM
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

    await security_expert(history=history)

    sent = fake_llm.calls[0]
    assert sent["messages"][0].content == "Security Expert system message"
    assert [tool.name for tool in sent["tools"]] == ["detect_exposed_secrets", "check_dependency"]

    # tools: a requested tool runs, instead of failing with "Error: ..."
    history = [
        Message(
            id="a1",
            owner=Owner.ASSISTANT,
            content="",
            tool_requests=[
                ToolRequest(id="t1", name="check_dependency", arguments={"package": "requests", "version": "2.19.1"})
            ],
        )
    ]

    tool_results = security_expert.run_tools(history=history, diff="")

    assert tool_results[0].content == "VULNERABLE: requests==2.19.1 (CVE-2018-18074)"

    # max_tool_rounds: the expert may run tools while under the limit of 3
    assert security_expert.should_continue(history=history, tool_rounds=2)
    assert not security_expert.should_continue(history=history, tool_rounds=3)

    # name and report_sys_message: what the report step sends and stamps
    history = [Message(id="a1", owner=Owner.ASSISTANT, content="")]
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

    findings, _ = await security_expert.format_report(history=history)

    assert fake_llm.calls[1]["messages"][0].content == "Security Expert report system message"
    assert findings[0].expert_name == "SecurityExpert"
