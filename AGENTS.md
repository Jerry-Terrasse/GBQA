# AGENTS.md

This file applies to the entire repository rooted here. Add more specific `AGENTS.md` files in subdirectories only when local rules need to override or refine these instructions.

## Project Purpose

GBQA is a research prototype for evaluating LLMs as game QA agents.

- The current baseline is a backend-API-driven text agent, not a browser/UI agent.
- The main benchmark target in this repo is `dark-castle`.
- The current roadmap still includes a future move from text actions to computer-use style interaction.

## Repository Map

- `agent/`: the QA agent, prompts, evaluation, reports, and memory.
- `agent/src/`: core runtime modules.
- `agent/src/computeruse/`: computer-use related backends and MCP transport helpers.
- `agent/run_agent.py`: main entry for running a QA session.
- `agent/run_eval.py`: evaluates an existing `report.md` against ground truth.
- `agent/config.yaml`: runtime settings for LLM, loop control, memory, targets, reporting, and evaluation.
- `agent/reports/<game_id>/<timestamp>/`: run artifacts.
- `agent/memory/<game_id>/`: session history and summary artifacts.
- `mytest/`: pytest-based contract and regression tests for the new execution stack.
- `hub/dark-castle/`: benchmark game, backend API, frontend, docs, and ground-truth bugs.
- `tmp/`: temporary notes, handoff docs, and disposable scripts.

## Environment And Commands

- Use the repo-level `uv` environment. Do not manage dependencies by editing files manually.
- For dependency changes, use `uv add` / `uv remove`.
- When running Python, prefer activating the existing virtual environment and then invoking Python directly.
- From the repo root, use `source .venv/bin/activate && ...`.
- From `agent/`, use `source ../.venv/bin/activate && ...`.

Useful commands:

- Run the agent:
  - `cd agent && source ../.venv/bin/activate && python run_agent.py --game dark-castle --config config.yaml --max-steps 50`
- Evaluate an existing report:
  - `cd agent && source ../.venv/bin/activate && python run_eval.py --game dark-castle --report reports/dark-castle/<run_id>/report.md`
- Smoke-test the CAMEL LLM path:
  - `cd agent && source ../.venv/bin/activate && python tmp/test_camel_api.py`
- Run the new pytest suite:
  - `source .venv/bin/activate && pytest mytest`

## Current Runtime Facts

- The main runtime is now `planner -> operator -> ExecutionBackend`, not planner-direct-to-client.
- `run_agent.py` builds an `ExecutionBackend`, an `Operator`, and an `Orchestrator`; it no longer closes a raw `GameClient` directly.
- The planner still outputs one text field per step via `Action.command`, but its semantics are now “single semantic action”, not necessarily a backend command string.
- `describe_capabilities` is a reserved planner action handled by the operator/backend layer; it must not be sent into the game environment as a normal game command.
- The orchestrator owns session lifecycle: it starts one backend session per run and closes it in the run-level `finally` path.
- The default backend remains `game_client`, wrapped by `GameClientExecutionBackend`.
- A `playwright_mcp` backend and `computeruse` module now exist, but this path should still be treated as an evolving browser pilot rather than a fully proven default runtime.
- The `playwright_mcp` path now supports screenshot actions. Screenshot artifacts are stored under `Observation.artifacts["screenshots"]`, and the planner can consume them through multimodal input.
- The observation model is still summary-first, but now includes normalized `summary`, `env_state`, `artifacts`, and `execution` fields in addition to the legacy compatibility fields.
- Reports are written incrementally during a run.

## Report And Evaluation Semantics

- Prefer `trace.jsonl` and `report.json` over `report.md` when debugging behavior.
- `report.md` is a lossy summary meant for humans.
- In `report.json`, step details are stored under `steps[].planner`, `steps[].environment`, and `steps[].reflection`.
- `steps[].environment.execution` is now the main place to inspect operator/backend attempts, diagnostics, and suspected failure origin.
- `run_eval.py` evaluates an existing `report.md`; it does not run the agent or the game.
- `report.md` bug formatting remains intentionally weakly compatible with `run_eval.py`; preserve the `## Bugs` / `### title` / `- Description:` structure unless you are also updating the evaluator.
- Evaluation uses LLM matching by default when an LLM client is available, with a similarity fallback.

## Dark Castle Ground Truth

The current benchmark file is `hub/dark-castle/bugs/dark-castle.json`. The three implanted bugs are:

1. The key can be combined after collecting only two fragments.
2. The bedroom description leaks the small key before opening the bedside drawer.
3. After dropping an item, a later `look` does not reflect the dropped item in the room description.

When assessing agent quality, distinguish between:

- a real gameplay inconsistency discovered during exploration, and
- a hit on the benchmark ground truth.

These are not the same thing.

## Known Pitfalls

- Reflection-based bug promotion can still report the same underlying bug multiple times.
- The current duplicate filter only compares bug-description text similarity, so paraphrased duplicates may pass through.
- Do not treat `Total bugs` in `report.md` as the number of unique root-cause issues without checking the report contents.
- `report.json` metadata is the first place to inspect LLM failures. Check `metadata.early_stop_reason`, `metadata.failed_stage`, `metadata.failed_step`, and `metadata.llm_error`.
- When debugging operator/backend failures, inspect `steps[].environment.execution.suspected_origin` before calling something a gameplay bug.
- Execution-layer failures should not be promoted as game bugs unless downstream reflection/evidence clearly reclassifies them as environment issues.
- Many LLM failures in this repo are provider/model-access problems rather than local code bugs.
- CAMEL does not automatically convert local image-path strings into uploaded image payloads. For multimodal prompts, pass `PIL.Image` objects rather than filesystem-path strings.
- `llm.timeout` in `agent/config.yaml` also affects the HTTP game client timeout in `run_agent.py`.

## Change Guidance

- Keep fixes targeted. This codebase is small, and behavior often depends on a few central files.
- If you change action, observation, memory, reporting, or evaluation semantics, inspect downstream consumers before editing.
- If you change planner/operator/backend boundaries, check prompts, structured outputs, orchestrator flow, bug detection, and report serialization together.
- Be careful when changing report formats; tests and ad hoc analysis scripts often assume the current schema.
- When fixing duplicate bug reporting, prefer reasoning in terms of unique bug identity or evidence updates, not only free-text similarity.
- If you work on computer-use support, treat it as a real action/observation model change rather than a model-swap task.
- Keep `game_client` compatibility working unless the task explicitly authorizes breaking it.
- Prefer adding contract tests for `ExecutionBackend`, operator retry behavior, and report compatibility when touching the new execution stack.

## Validation Expectations

After code changes, run the smallest checks that meaningfully cover the affected area.

- For LLM connectivity or provider configuration: `python tmp/test_camel_api.py`
- For platform resolution and CAMEL fallback logic: inspect relevant tests under `agent/test/`
- For report/evaluator changes: verify both `report.json` structure and `run_eval.py` behavior
- For dark-castle API interactions: use the existing client smoke tests before attempting long agent runs
- For execution-stack changes: run the relevant `agent/test/` smoke tests and `pytest mytest`

Useful test files include:

- `agent/test/test_dark_castle_client.py`
- `agent/test/test_model_platform_resolution.py`
- `agent/test/test_camel_runtime_fallback.py`
- `agent/test/test_game_client_backend_loop.py`
- `agent/test/test_describe_capabilities.py`
- `agent/test/test_planner_multimodal.py`
- `agent/test/test_playwright_screenshot_artifact.py`
- `agent/test/test_report_markdown_compat.py`
- `agent/test/test_orchestrator_bug_promotion.py`
- `agent/test/test_bug_detector.py`
- `agent/test/test_evaluator_ground_truth.py`
- `mytest/test_game_client_backend.py`
- `mytest/test_operator.py`
- `mytest/test_orchestrator_session.py`
- `mytest/test_playwright_backend.py`
- `mytest/test_reporter.py`

## Working Conventions For This Repo

- Respond to the human collaborator in Chinese unless explicitly asked otherwise.
- Write code comments in English, and only when the code is not self-explanatory.
- Place temporary scripts, notes, handoff docs, and disposable artifacts under `tmp/`.
- Treat a repo-root `AGENTS.md` as a special instruction file, not as ordinary project documentation.
