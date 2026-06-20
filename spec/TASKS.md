# PAI — Tasks

Living TDD checklist. Each implementation task is preceded by its test (write the failing test
first, then the minimal code to pass it). See `PHASES.md` for the milestone view.

## Phase 0 — Spec + SDLC

- [x] `spec/OVERVIEW.md`
- [x] `spec/ARCHITECTURE.md`
- [x] `spec/REFERENCES.md`
- [x] `spec/PHASES.md`
- [x] `spec/TASKS.md`
- [ ] `AGENTS.md`
- [ ] `pyproject.toml`: dev group (pytest, ruff, ty), `[tool.ruff]`, `[tool.ty]`,
      `[tool.pytest.ini_options]`, fix `[project.scripts]` → `pai.cli:main`
- [ ] `.pre-commit-config.yaml` (ruff lint+format, ty, hygiene) for prek
- [ ] `.gitignore` (add `.pai/`)
- [ ] `uv sync` works

## Phase 1 — Core pipeline + exceptions (TDD)

### run.py — run identity + paths
- [ ] test: run-id format + uniqueness; `create_run_dir` makes dir + `latest` pointer
- [ ] impl: `new_run_id()`, `runs_root()`, `create_run_dir()`, `latest_pointer()`

### runner.py — env injection + subprocess
- [ ] test: `build_env` prepends bootstrap dir to `PYTHONPATH` (preserving existing), sets
      `PAI_RUN_DIR`
- [ ] impl: `build_env(run_dir)`, `run(argv) -> int`

### writer.py — event sink
- [ ] test: appends valid JSONL; thread-safe under concurrent writes; per-type fan-out file
- [ ] impl: `EventWriter` (open, `write(event)`, lock, flush, per-type files, close)

### events.py — event model
- [ ] test: `ExceptionEvent.to_dict()` matches Example 1 shape
- [ ] impl: base event + `ExceptionEvent` + `LocalSchema` TypedDict

### collectors/exceptions.py — exception collector
- [ ] test: build event from a synthetic traceback (symbol, line, `locals_schema`)
- [ ] impl: `build_exception_event(...)`, `install(writer)` wiring excepthooks

### bootstrap/sitecustomize.py — injection entrypoint
- [ ] impl: read `PAI_RUN_DIR`, create writer, install collectors, chain prior sitecustomize

### cli.py — command line
- [ ] impl: argparse `main()` with `run` subcommand → `runner.run`

### integration
- [ ] test: `pai run python <fixture>` writes `events.jsonl` with the expected exception event
      (`symbol`, `exception_type`, `message`, `locals_schema.payload.keys == ["name"]`)

## Verification
- [x] `uv run pytest` green (18 passing)
- [x] `uv run ruff check . && uv run ruff format --check .` clean
- [x] `uv run ty check` clean
- [x] `prek run --all-files` passes
- [x] manual e2e (idea-doc Example 1) — confirmed `run_start` → `exception` → `run_end`

## Backlog (deferred — see PHASES.md)
- [ ] P2 import graph (ast static analysis + import hooks)
- [ ] P3 runtime call tracing + timing (setprofile)
- [ ] P4 pytest plugin — test intelligence (failure ↔ covered functions)
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
