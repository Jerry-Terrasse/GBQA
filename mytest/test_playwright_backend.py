from __future__ import annotations

from src.computeruse.playwright_backend import (
    PlaywrightMcpExecutionBackend,
    PlaywrightMcpSettings,
)
from src.types import ExecutionCall, ExecutionRequest


class FakeMcpClient:
    def __init__(self) -> None:
        self.calls = []
        self.started = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def list_tools(self):
        return {
            "tools": [
                {"name": "browser_navigate"},
                {"name": "browser_click"},
                {"name": "browser_type"},
                {"name": "browser_snapshot"},
                {"name": "browser_wait_for"},
            ]
        }

    def call_tool(self, name, arguments):  # noqa: ANN001
        self.calls.append((name, arguments))
        if name == "browser_snapshot":
            return {
                "content": [
                    {
                        "text": (
                            "### Page\n"
                            "- Page URL: http://localhost:5000/\n"
                            "### Snapshot\n"
                            "```yaml\n"
                            "- generic [active] [ref=e1]:\n"
                            "  - generic [ref=e8]:\n"
                            "    - generic [ref=e9]:\n"
                            "      - generic [ref=e11]: \"Location:\"\n"
                            "      - generic [ref=e12]: Hall\n"
                            "    - generic [ref=e13]:\n"
                            "      - generic [ref=e15]: \"Inventory:\"\n"
                            "      - generic [ref=e16]: 0/6\n"
                            "    - generic [ref=e17]:\n"
                            "      - generic [ref=e19]: \"Turn:\"\n"
                            "      - generic [ref=e20]: \"1\"\n"
                            "    - generic [ref=e21]:\n"
                            "      - generic [ref=e23]: No light\n"
                            "    - main [ref=e24]:\n"
                            "      - paragraph [ref=e28]: Press the button below to begin your escape.\n"
                            "      - button \"Inventory\" [ref=e50] [cursor=pointer]\n"
                            "      - button \"Help\" [ref=e51] [cursor=pointer]\n"
                            "      - button \"Combine\" [ref=e52] [cursor=pointer]\n"
                            "      - 'textbox \"Enter a command...\" [ref=e56]'\n"
                            "      - button \"Send\" [ref=e57] [cursor=pointer]\n"
                            "      - button \"Start New Game\" [ref=e58] [cursor=pointer]\n"
                            "```"
                        )
                    }
                ]
            }
        return {"content": [{"text": "ok"}]}

    def close(self) -> None:
        self.closed = True


def test_playwright_backend_normalizes_capabilities_and_observation() -> None:
    fake_client = FakeMcpClient()
    backend = PlaywrightMcpExecutionBackend(
        settings=PlaywrightMcpSettings(
            command=["fake"],
            startup_timeout=5,
            frontend_url="http://localhost:5000",
            snapshot_tool="browser_snapshot",
            screenshot_tool="browser_take_screenshot",
            navigate_tool="browser_navigate",
            click_tool="browser_click",
            type_tool="browser_type",
            press_tool="browser_press_key",
            wait_tool="browser_wait_for",
            screenshot_dir="tmp/playwright_artifacts",
        ),
        client_factory=lambda: fake_client,
    )

    session = backend.start_session({})
    capability = backend.describe_capabilities(session)
    assert "browser UI" in capability.planner_summary
    assert "browser_click" in capability.operator_context["available_tools"]
    assert capability.operator_context["requires_ref_for_kinds"] == ["click", "type"]

    result = backend.execute(
        session,
        ExecutionRequest(
            planner_action="点击 Start New Game 按钮",
            calls=[ExecutionCall(kind="click", ref="e58", target="Start New Game")],
        ),
    )
    assert result.observation.success is True
    assert result.observation.summary.startswith("### Page\n- Page URL:")
    assert result.observation.summary == result.observation.message
    assert result.observation.env_state["status_bar"]["location"] == "Hall"
    assert result.observation.env_state["actionable_elements"][-1]["ref"] == "e58"
    assert "Visible controls" in result.observation.env_state["controls_summary"]
    backend.close_session(session)
    assert fake_client.closed is True


def test_playwright_backend_classifies_tool_iserror_as_execution_failure() -> None:
    class ErrorClient(FakeMcpClient):
        def call_tool(self, name, arguments):  # noqa: ANN001
            self.calls.append((name, arguments))
            if name == "browser_snapshot":
                return super().call_tool(name, arguments)
            return {
                "isError": True,
                "content": [{"type": "text", "text": "Invalid ref"}],
            }

    fake_client = ErrorClient()
    backend = PlaywrightMcpExecutionBackend(
        settings=PlaywrightMcpSettings(
            command=["fake"],
            startup_timeout=5,
            frontend_url="http://localhost:5000",
            snapshot_tool="browser_snapshot",
            screenshot_tool="browser_take_screenshot",
            navigate_tool="browser_navigate",
            click_tool="browser_click",
            type_tool="browser_type",
            press_tool="browser_press_key",
            wait_tool="browser_wait_for",
            screenshot_dir="tmp/playwright_artifacts",
        ),
        client_factory=lambda: fake_client,
    )

    session = backend.start_session({})
    result = backend.execute(
        session,
        ExecutionRequest(
            planner_action="click Start New Game",
            calls=[ExecutionCall(kind="click", ref="missing", target="Start New Game")],
        ),
    )

    assert result.observation.success is False
    assert result.observation.execution["suspected_origin"] == "execution"
    assert result.observation.execution["diagnostics"]["error"] == "Invalid ref"
