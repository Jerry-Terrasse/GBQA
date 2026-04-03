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
- `agent/run_agent.py`: main entry for running a QA session.
- `agent/run_eval.py`: evaluates an existing `report.md` against ground truth.
- `agent/config.yaml`: runtime settings for LLM, loop control, memory, targets, reporting, and evaluation.
- `agent/reports/<game_id>/<timestamp>/`: run artifacts.
- `agent/memory/<game_id>/`: session history and summary artifacts.
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

## Current Runtime Facts

- `run_agent.py` creates an HTTP game client and registers `game_new`, `game_command`, and `game_state`.
- The planner currently outputs one text `command` per step.
- The orchestrator sends that command to `game_command` and parses text/state responses.
- The observation model is still text-first; it does not yet include screenshots, DOM trees, or browser actions.
- Reports are written incrementally during a run.

## Report And Evaluation Semantics

- Prefer `trace.jsonl` and `report.json` over `report.md` when debugging behavior.
- `report.md` is a lossy summary meant for humans.
- In `report.json`, step details are stored under `steps[].planner`, `steps[].environment`, and `steps[].reflection`.
- `run_eval.py` evaluates an existing `report.md`; it does not run the agent or the game.
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
- Many LLM failures in this repo are provider/model-access problems rather than local code bugs.
- `llm.timeout` in `agent/config.yaml` also affects the HTTP game client timeout in `run_agent.py`.

## Change Guidance

- Keep fixes targeted. This codebase is small, and behavior often depends on a few central files.
- If you change action, observation, memory, reporting, or evaluation semantics, inspect downstream consumers before editing.
- Be careful when changing report formats; tests and ad hoc analysis scripts often assume the current schema.
- When fixing duplicate bug reporting, prefer reasoning in terms of unique bug identity or evidence updates, not only free-text similarity.
- If you work on future computer-use support, treat it as a real action/observation model change rather than a model-swap task.

## Validation Expectations

After code changes, run the smallest checks that meaningfully cover the affected area.

- For LLM connectivity or provider configuration: `python tmp/test_camel_api.py`
- For platform resolution and CAMEL fallback logic: inspect relevant tests under `agent/test/`
- For report/evaluator changes: verify both `report.json` structure and `run_eval.py` behavior
- For dark-castle API interactions: use the existing client smoke tests before attempting long agent runs

Useful test files include:

- `agent/test/test_dark_castle_client.py`
- `agent/test/test_model_platform_resolution.py`
- `agent/test/test_camel_runtime_fallback.py`
- `agent/test/test_orchestrator_bug_promotion.py`
- `agent/test/test_evaluator_ground_truth.py`

## Working Conventions For This Repo

- Respond to the human collaborator in Chinese unless explicitly asked otherwise.
- Write code comments in English, and only when the code is not self-explanatory.
- Place temporary scripts, notes, handoff docs, and disposable artifacts under `tmp/`.
- Treat a repo-root `AGENTS.md` as a special instruction file, not as ordinary project documentation.
