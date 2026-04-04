from __future__ import annotations

import json
from pathlib import Path

from run_eval import parse_report_bugs
from src.reporter import Reporter
from src.types import Action, BugFinding, Observation, RunReport, StepRecord


def test_reporter_writes_extended_json_and_compatible_markdown(temp_dir) -> None:
    reporter = Reporter(str(temp_dir), "dark-castle")
    report = RunReport(
        game_id="dark-castle",
        steps=[
            StepRecord(
                step=1,
                action=Action(command="look", rationale="inspect room"),
                observation=Observation(
                    success=True,
                    message="You are in the hall.",
                    state={"room": {"name": "Hall"}},
                    summary="You are in the hall.\n\ncurrent room=Hall",
                    env_state={"room_name": "Hall"},
                    execution={
                        "attempts": [],
                        "diagnostics": {"backend_type": "game_client"},
                    },
                ),
                planner_prompt="prompt",
                planner_output='{"command":"look"}',
                capability_summary="command backend",
            )
        ],
        bugs=[
            BugFinding(
                title="State mismatch",
                description="The room description did not update after drop.",
                confidence=0.8,
            )
        ],
    )

    paths = reporter.write_report(report)
    payload = json.loads(Path(paths["json"]).read_text(encoding="utf-8"))
    assert payload["steps"][0]["planner"]["action"] == "look"
    assert payload["steps"][0]["environment"]["summary"].startswith("You are in the hall.")
    assert payload["steps"][0]["environment"]["execution"]["diagnostics"]["backend_type"] == "game_client"

    parsed_bugs = parse_report_bugs(paths["markdown"])
    assert parsed_bugs[0].title == "State mismatch"
