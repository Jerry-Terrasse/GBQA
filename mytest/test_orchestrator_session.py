from __future__ import annotations

from src.orchestrator import Orchestrator
from src.types import Action, CapabilityDescriptor, Observation, SessionHandle


class PlannerStub:
    def __init__(self) -> None:
        self.last_context = None

    def plan(self, context):  # noqa: ANN001
        self.last_context = context
        return type(
            "PlanResult",
            (),
            {
                "action": Action(command="describe_capabilities"),
                "prompt": "planner prompt",
                "output": '{"command":"describe_capabilities"}',
                "error": "",
            },
        )()


class OperatorStub:
    def execute(self, **kwargs):  # noqa: ANN003
        return type(
            "Result",
            (),
            {
                "observation": Observation(
                    success=True,
                    message="capability summary",
                    state={},
                    summary="capability summary",
                    execution={
                        "attempts": [],
                        "diagnostics": {"source": "describe_capabilities"},
                    },
                ),
                "attempts": [],
                "diagnostics": {},
            },
        )()


class BackendStub:
    backend_type = "game_client"

    def __init__(self) -> None:
        self.closed = False
        self.refresh_calls = 0

    def start_session(self, run_context):  # noqa: ANN001
        return SessionHandle(
            session_id="session-1",
            backend_type=self.backend_type,
            initial_observation=Observation(
                success=True,
                message="initial",
                state={},
                summary="initial",
            ),
        )

    def describe_capabilities(self, session, refresh=False):  # noqa: ANN001
        if refresh:
            self.refresh_calls += 1
        return CapabilityDescriptor(
            planner_summary="capability summary",
            operator_context={"translation_mode": "transparent_command"},
        )

    def close_session(self, session):  # noqa: ANN001
        self.closed = True


class MemoryStub:
    def get_long_term_summary(self) -> str:
        return ""

    def get_cross_session_memories(self, query):  # noqa: ANN001
        return []

    def get_recent_trace(self) -> str:
        return ""

    def record_step(self, record):  # noqa: ANN001
        return None

    def record_bug(self, bug, step):  # noqa: ANN001
        return None

    def force_summarize(self, step):  # noqa: ANN001
        return None

    def maybe_summarize(self, step):  # noqa: ANN001
        return None


class ReporterStub:
    def log_step(self, record):  # noqa: ANN001
        return None

    def log_bug(self, bug, step):  # noqa: ANN001
        return None

    def log_summary(self, summary, step):  # noqa: ANN001
        return None

    def write_report(self, report):  # noqa: ANN001
        return {}


def test_orchestrator_manages_session_lifecycle() -> None:
    backend = BackendStub()
    planner = PlannerStub()
    orchestrator = Orchestrator(
        game_id="dark-castle",
        execution_backend=backend,
        operator=OperatorStub(),
        planner=planner,
        memory=MemoryStub(),
        detector=None,
        reporter=ReporterStub(),
        evaluator=None,
        max_steps=1,
        reflection_analyzer=None,
        reflection_threshold=3,
        max_consecutive_failures=5,
        confidence_threshold=0.7,
        reflection_interval=10,
        summary_interval=40,
    )

    report = orchestrator.run("profile")
    assert report.metadata["backend"]["type"] == "game_client"
    assert report.metadata["session_id"] == "session-1"
    assert backend.closed is True
    assert backend.refresh_calls == 0
    assert "Capability observation:" in planner.last_context["current_observation"]
    assert "Initial environment observation:" in planner.last_context["current_observation"]
