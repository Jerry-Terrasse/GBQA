from __future__ import annotations

from src.execution_backends import GameClientExecutionBackend
from src.types import ExecutionCall, ExecutionRequest


class FakeGameClient:
    def __init__(self) -> None:
        self.closed = False
        self.commands = []

    def new_game(self):
        return {
            "game_id": "session-1",
            "success": True,
            "message": "Welcome to the hall.",
            "state": {"room": {"name": "Hall", "exits": ["north"]}, "inventory": []},
            "turn": 0,
        }

    def send_command(self, game_id, command):  # noqa: ANN001
        self.commands.append((game_id, command))
        return {
            "success": True,
            "message": "You look around.",
            "state": {"room": {"name": "Hall", "exits": ["north"]}, "inventory": []},
            "turn": 1,
            "game_over": False,
        }

    def get_state(self, game_id):  # noqa: ANN001
        raise AssertionError("unused")

    def close(self) -> None:
        self.closed = True


def test_game_client_backend_contract() -> None:
    backend = GameClientExecutionBackend(FakeGameClient())
    session = backend.start_session({"game_id": "dark-castle"})

    capability = backend.describe_capabilities(session)
    assert "text-command game backend" in capability.planner_summary
    assert capability.operator_context["translation_mode"] == "transparent_command"

    result = backend.execute(
        session,
        ExecutionRequest(
            planner_action="look",
            calls=[ExecutionCall(kind="send_game_command", text="look")],
        ),
    )

    assert result.observation.success is True
    assert result.observation.summary.startswith("You look around.")
    assert "suspected_origin" not in result.observation.execution
    backend.close_session(session)
