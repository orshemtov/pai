# PAI — Tasks

Living TDD checklist. Each implementation task is preceded by its test (write the failing test
first, then the minimal code to pass it). See `PHASES.md` for the milestone view.

## Phase 0 — Spec + SDLC

- [x] `spec/OVERVIEW.md`
- [x] `spec/ARCHITECTURE.md`
- [x] `spec/REFERENCES.md`
- [x] `spec/PHASES.md`
- [x] `spec/TASKS.md`
- [x] `AGENTS.md`
- [x] `pyproject.toml`: dev group (pytest, ruff, ty), `[tool.ruff]`, `[tool.ty]`,
      `[tool.pytest.ini_options]`, fix `[project.scripts]` → `pai.cli:main`
- [x] `.pre-commit-config.yaml` (ruff lint+format, ty, hygiene) for prek
- [x] `.gitignore` (add `.pai/`)
- [x] `uv sync` works
- [x] `mise.toml` task runner (test, lint, format, typecheck, check, ci, hooks)

## Phase 1 — Core pipeline + exceptions (TDD)

- [x] test + impl: `new_run_id()`, `runs_root()`, `create_run_dir()`, `latest_pointer()`
- [x] test + impl: `build_env` (PYTHONPATH + PAI_RUN_DIR injection), `run(argv) -> int`
- [x] test + impl: `EventWriter` — JSONL append, thread-safe, per-type fan-out
- [x] test + impl: `ExceptionEvent.to_dict()` matches Example 1 shape
- [x] test + impl: `build_exception_event` from synthetic traceback (symbol, line, `locals_schema`)
- [x] impl: `bootstrap/sitecustomize.py` — read `PAI_RUN_DIR`, install collectors, chain prior
- [x] impl: `pai run <cmd>` CLI
- [x] integration test: `pai run python <fixture>` → structured exception event in `events.jsonl`

## Phase 2 — Import graph

- [x] `ImportEvent(module, imported)` — one event per import edge
- [x] `ImportCollector` class (DI: writer + original `builtins.__import__`)
- [x] `resolve_module_name` — absolute + relative import resolution
- [x] Wired into `sitecustomize.py`
- [x] Unit tests (resolve, dedup, different callers, None globals)
- [x] Integration test: `pai run python <script with imports>` → import events in `events.jsonl`

## Phase 3 — Runtime call tracing

- [x] `CallEvent(caller, callee, file, line, duration_ms)`
- [x] `CallCollector` class (DI: writer + original profile); `should_trace_frame` filters PAI internals
- [x] `sys.setprofile` + `threading.setprofile` wired in `sitecustomize.py`
- [x] Unit tests (emits event, records caller, duration, file/line, chains original, filters internals)
- [x] Integration test: `pai run python <script with function calls>` → call events

## Phase 4 — Pytest plugin

- [x] `TestEvent(test_id, outcome, duration_ms, file, message)`
- [x] `src/pai/pytest_plugin.py` — `PaiPlugin` class; registered via `pytest11` entry point
- [x] No-op when `PAI_RUN_DIR` not set; emits one `TestEvent` per test item (when=call only)
- [x] `pyproject.toml`: `[project.entry-points.pytest11]` registration
- [x] Tests: passing, failing, duration, file, multiple tests, noop without run dir

## Verification (current)

- [x] `uv run pytest` — 45 passing
- [x] `uv run ruff check . && uv run ruff format --check .` — clean
- [x] `uv run ty check` — clean
- [x] `mise run ci` — green

## Backlog (deferred — see PHASES.md)

- [ ] P5 side-effect tracing — initial: requests, httpx, boto3/aioboto3, sqlalchemy, asyncpg.
      Future: openai, anthropic, redis, celery. Ref: ddtrace supported-libraries.
- [ ] P6 `pai bundle` + symbol graph

## Zerolang learnings (adopted or deferred)

Adopted (done):
- [x] Schema version on every event (`schema_version: 1`)
- [x] Timestamp on every event (injected by writer)
- [x] `RunStartEvent` — captures command, cwd, python_version at process start
- [x] `RunEndEvent` — captures exit_code, duration_ms after subprocess exits

Deferred (future consideration):
- [ ] `pai query` — hierarchical inspection API (status → narrow → full snapshot)
      to control token budget when agents query events
- [ ] Watch / plan mode — `pai watch <cmd>`, returns what files changed + what re-ran
- [ ] Fix-guidance tags on exception events (e.g. "fixSafety" level)
- [ ] Capability / side-effect declaration (what the process touched: fs, net, db)
