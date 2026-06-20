# PAI — Architecture

## Core mechanism

PAI wraps Python execution similarly to `ddtrace-run`: it runs your command as a subprocess,
but first arranges for a **bootstrap module** to be imported automatically into that process.

```bash
pai run python app.py
pai run pytest
pai run uvicorn app.main:app
```

The wrapper (`pai run`) does three things and then `exec`s/spawns the target command:

1. Creates a run directory: `.pai/runs/<run-id>/` (plus a `latest` pointer).
2. Builds an environment that injects PAI into the child:
   - Prepends PAI's **bootstrap directory** to `PYTHONPATH`. That directory contains a
     `sitecustomize.py`, which CPython imports automatically at interpreter startup.
   - Sets `PAI_RUN_DIR` so the injected code knows where to write events.
3. Spawns the target command and returns its exit code unchanged.

Because injection happens through `PYTHONPATH` + `sitecustomize`, the target application needs
no modification.

```
pai run python app.py
        │
        ├─ create .pai/runs/<id>/ , point latest → it
        ├─ env: PYTHONPATH = <bootstrap_dir>:$PYTHONPATH ; PAI_RUN_DIR = <id>
        └─ subprocess(python app.py)
                 │  (interpreter startup imports sitecustomize)
                 └─ pai/bootstrap/sitecustomize.py
                          ├─ chain any pre-existing sitecustomize
                          └─ install collectors → write events.jsonl
```

## Hard constraint: zero runtime dependencies

The bootstrap and collector code is imported **into the target process**, so it shares that
process's environment. To avoid version conflicts or polluting the target app, the
**runtime path uses the Python standard library only** (`dataclasses`, `typing`, `json`,
`sys`, `threading`, `ast`, `pathlib`, …). PAI declares **no runtime dependencies**.

Dev-only tooling (pytest, ruff, ty, prek) is unrestricted and lives in the dev dependency
group.

## Runtime hooks

Collectors install themselves via CPython runtime hooks:

- `sitecustomize` — entry point for injection.
- `sys.excepthook` / `threading.excepthook` — uncaught exceptions (MVP).
- `sys.setprofile` — call tracing (later).
- import hooks (`sys.meta_path`) — import graph (later).
- pytest plugin — test intelligence (later).

## Framework integrations (later)

FastAPI, Flask, Django, SQLAlchemy, Requests, HTTPX, boto3 / aioboto3, OpenTelemetry.
Installed conditionally — only when the target imports them.

## Event storage

All events are appended to a single newline-delimited JSON file:

```text
.pai/runs/<run-id>/events.jsonl
```

```json
{"event":"exception", ...}
{"event":"call", ...}
```

For convenience, the writer also fans out per-type files (e.g. `exceptions.json`) used by the
`bundle` output. Agents consume these structured files instead of terminal output.

## Module layout (`src/pai/`)

```
pai/
├── __init__.py          # package marker; minimal public surface
├── cli.py               # argparse CLI: main(), `run` subcommand
├── runner.py            # build_env(), run(argv) -> exit code
├── run.py               # run-id, run-dir paths, latest pointer
├── events.py            # @dataclass event types + TypedDict schemas
├── writer.py            # EventWriter: thread-safe JSONL append + fan-out
├── bootstrap/
│   └── sitecustomize.py # injected; installs collectors, chains prior sitecustomize
└── collectors/
    └── exceptions.py    # excepthook + threading.excepthook → ExceptionEvent
```

Modules are split by cohesion. Files stay under 500 lines; symbols are private unless
explicitly exported via `__all__` / `__init__.py`.

## Tech stack

- **Language:** Python 3.13 (stdlib only at runtime).
- **Build / env:** uv (`uv_build` backend).
- **Lint + format:** ruff.
- **Type checking:** ty (Astral).
- **Tests:** pytest, TDD.
- **Pre-commit:** prek.

## Data model

Events are `@dataclass` records with an `event` string tag and a `to_dict()` serializer.
Known-shape nested dicts (e.g. a `locals_schema` entry `{type, keys?}`) are typed with
`TypedDict`. The writer serializes `to_dict()` output to JSON, one event per line.
