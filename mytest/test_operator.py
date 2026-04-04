from __future__ import annotations

from src.operator import Operator
from src.structured_outputs import OperatorCallDecision, OperatorDecision
from src.types import (
    Action,
    BackendExecutionResult,
    CapabilityDescriptor,
    ExecutionAttempt,
    ExecutionRequest,
    Observation,
    SessionHandle,
)


class FakeAgent:
    def __init__(self, responses):
        self._responses = list(responses)

    def run(self, prompt, response_format=None):  # noqa: ANN001
        response = self._responses.pop(0)
        return type(
            "Response",
            (),
            {
                "parsed": response,
                "content": "",
                "error": "",
            },
        )()


class FakeLlmClient:
    def __init__(self, responses):
        self._responses = responses

    def create_task_agent(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return FakeAgent(self._responses)


class RetryBackend:
    backend_type = "playwright_mcp"

    def __init__(self) -> None:
        self.calls = 0

    def describe_capabilities(self, session, refresh=False):  # noqa: ANN001
        return CapabilityDescriptor(
            planner_summary="browser",
            operator_context={"translation_mode": "llm_first"},
        )

    def execute(self, session, request: ExecutionRequest):  # noqa: ANN001
        self.calls += 1
        if self.calls == 1:
            observation = Observation(
                success=False,
                message="Element not found",
                state={},
                summary="Execution failure in Playwright MCP: Element not found",
                execution={
                    "attempts": [],
                    "diagnostics": {"error": "Element not found", "error_kind": "element_not_found"},
                    "suspected_origin": "execution",
                },
            )
            return BackendExecutionResult(
                observation=observation,
                attempts=[
                    ExecutionAttempt(
                        attempt=1,
                        translated_calls=request.calls,
                        success=False,
                        final_status="failed",
                        suspected_origin="execution",
                        error="Element not found",
                    )
                ],
                diagnostics={"error": "Element not found"},
            )
        observation = Observation(
            success=True,
            message="Snapshot text",
            state={},
            summary="Recovered after retry",
            execution={
                "attempts": [],
                "diagnostics": {},
                "suspected_origin": "environment",
            },
        )
        return BackendExecutionResult(
            observation=observation,
            attempts=[
                ExecutionAttempt(
                    attempt=1,
                    translated_calls=request.calls,
                    success=True,
                    final_status="completed",
                    suspected_origin="environment",
                )
            ],
            diagnostics={},
        )


def test_operator_retries_retryable_execution_errors() -> None:
    operator = Operator(
        FakeLlmClient(
            [
                OperatorDecision(calls=[OperatorCallDecision(kind="snapshot")]),
                OperatorDecision(calls=[OperatorCallDecision(kind="snapshot")]),
            ]
        ),
        "unused",
        max_retries=2,
    )
    capability = CapabilityDescriptor(
        planner_summary="browser",
        operator_context={"translation_mode": "llm_first"},
    )
    result = operator.execute(
        action=Action(command="读取输出面板最新内容"),
        current_observation=Observation(success=True, message="", state={}, summary=""),
        capability=capability,
        session=SessionHandle(session_id="s1", backend_type="playwright_mcp"),
        backend=RetryBackend(),
    )

    assert result.observation.success is True
    assert result.observation.execution["diagnostics"]["attempt_count"] == 2
    assert len(result.attempts) == 2


def test_operator_returns_execution_failure_on_translation_error() -> None:
    backend = RetryBackend()
    operator = Operator(FakeLlmClient([None]), "unused", max_retries=1)
    capability = CapabilityDescriptor(
        planner_summary="browser",
        operator_context={"translation_mode": "llm_first"},
    )
    result = operator.execute(
        action=Action(command="click Start New Game"),
        current_observation=Observation(success=True, message="", state={}, summary=""),
        capability=capability,
        session=SessionHandle(session_id="s1", backend_type="playwright_mcp"),
        backend=backend,
    )

    assert result.observation.success is False
    assert result.observation.execution["suspected_origin"] == "execution"
    assert result.observation.execution["diagnostics"]["error_kind"] == "translation_error"
    assert backend.calls == 0


def test_operator_requires_ref_for_click_calls_when_backend_demands_it() -> None:
    operator = Operator(
        FakeLlmClient([OperatorDecision(calls=[OperatorCallDecision(kind="click", target="Start New Game")])]),
        "unused",
        max_retries=1,
    )
    capability = CapabilityDescriptor(
        planner_summary="browser",
        operator_context={
            "translation_mode": "llm_first",
            "requires_ref_for_kinds": ["click", "type"],
        },
    )
    result = operator.execute(
        action=Action(command="click Start New Game"),
        current_observation=Observation(
            success=True,
            message="",
            state={},
            summary="",
            env_state={"actionable_elements": [{"role": "button", "label": "Start New Game", "ref": "e58", "enabled": True}]},
        ),
        capability=capability,
        session=SessionHandle(session_id="s1", backend_type="playwright_mcp"),
        backend=RetryBackend(),
    )

    assert result.observation.success is False
    assert result.observation.execution["diagnostics"]["error_kind"] == "translation_error"


def test_operator_handles_describe_capabilities_without_backend_execute_calls() -> None:
    backend = RetryBackend()
    operator = Operator(FakeLlmClient([]), "unused", max_retries=1)
    capability = CapabilityDescriptor(
        planner_summary="summary text",
        operator_context={"translation_mode": "transparent_command"},
    )
    result = operator.execute(
        action=Action(command="describe_capabilities"),
        current_observation=Observation(success=True, message="", state={}, summary=""),
        capability=capability,
        session=SessionHandle(session_id="s1", backend_type="game_client"),
        backend=backend,
    )

    assert result.observation.summary == "browser"
    assert backend.calls == 0
