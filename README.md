# PAI

Agent-native runtime output for Python.

[![CI](https://github.com/orshemtov/pai/actions/workflows/ci.yml/badge.svg)](https://github.com/orshemtov/pai/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Runtime deps: zero](https://img.shields.io/badge/runtime%20deps-zero-brightgreen.svg)](pyproject.toml)

PAI lets coding agents run Python programs and receive structured facts about
what happened: exceptions, imports, function calls, tests, run metadata, and
side effects.

Humans keep writing ordinary Python. Agents stop scraping terminal text.

```bash
pai run pytest
pai bundle --run .pai/runs/latest
```

## Why PAI Exists

Python is already the language people use. The missing layer is not a new syntax
for humans; it is a better runtime interface for agents.

Today, agents infer program behavior from human-shaped output:

- tracebacks
- pytest prose
- console logs
- scattered files
- noisy command output

PAI turns the same execution into machine-readable JSON. An agent can inspect the
run directly instead of spending tokens reconstructing facts from text.

The model is simple:

```text
normal Python source
        |
        v
pai run <command>
        |
        v
structured runtime events
        |
        v
agent reads facts, repairs code, reruns
```

This is inspired by agent-first systems such as graph-oriented languages, but
keeps Python source as the durable artifact. PAI adds an agent-facing execution
layer around the language people already use.

## Agent Quick Start

Use a checkout until the first package release is published:

```bash
git clone https://github.com/orshemtov/pai.git
cd pai
uv sync
uv run pai run python --version
```

Run the target command through PAI:

```bash
pai run python app.py
pai run pytest
pai run uvicorn app.main:app
```

Read the latest run:

```bash
pai query status
pai query failures
pai bundle --run .pai/runs/latest
```

The planned PyPI distribution is `pai-trace` because `pai` is already used on
PyPI. The CLI command and Python import package are still named `pai`.

## What Agents Get

PAI writes newline-delimited JSON to:

```text
.pai/runs/latest/events.jsonl
```

It also creates a grouped bundle:

```bash
pai query status
pai query failures
pai query tests
pai query effects
pai query timeline --limit 50
pai query symbol --name app.parse_user
pai query repair-context --event evt_000003
pai bundle --run .pai/runs/latest --out pai-bundle.json
```

Event families:

| Event | Agent-facing fact |
| --- | --- |
| `run_start` / `run_end` | Command, cwd, Python version, exit code, duration |
| `exception` | Failing symbol, file, line, exception type, message, local schemas |
| `import` | Runtime import edges |
| `call` | App-owned function calls and duration |
| `test` | Pytest item outcome, duration, file, message |
| `requests`, `httpx`, `sqlalchemy`, `asyncpg`, `boto3`, `aiobotocore`, `openai`, `anthropic` | Side-effect events by concrete package |

Each emitted event includes:

- `run_id`: the run directory name.
- `event_id`: a stable per-run handle like `evt_000003`.
- `timestamp`: when PAI wrote the event.

Agents should use these handles for follow-up queries instead of reloading full
logs.

Example exception event:

```json
{
  "run_id": "20260620T120000-abc12345",
  "event_id": "evt_000003",
  "event": "exception",
  "schema_version": 1,
  "symbol": "__main__.parse_user",
  "file": "app.py",
  "line": 2,
  "exception_type": "KeyError",
  "message": "'user_id'",
  "locals_schema": {
    "payload": {
      "type": "dict",
      "keys": ["name"]
    }
  }
}
```

Agents should prefer this data over terminal output.

## Query Workflow

For most agent loops, inspect data in this order:

```bash
pai run --summary-json pytest
pai query status
pai query failures
pai query repair-context --event <event_id>
```

Use `pai bundle` only when the agent needs the full run artifact.

## Privacy Contract

PAI records schemas, not values.

For exception locals, PAI records type names and dict keys. It does not serialize
raw user data into events. A local variable like this:

```python
payload = {"name": "Ada", "email": "ada@example.com"}
```

is captured as shape:

```json
{
  "payload": {
    "type": "dict",
    "keys": ["email", "name"]
  }
}
```

## How It Works

`pai run` starts the target command with a modified environment:

- prepends PAI's bootstrap directory to `PYTHONPATH`
- sets `PAI_RUN_DIR`
- lets CPython import `sitecustomize`
- installs collectors inside the target process
- returns the target exit code unchanged

The runtime path is standard-library-only. PAI does not add dependencies to the
target application environment.

## Agent Skill

Agent instructions live in [`skill/SKILL.md`](skill/SKILL.md). Use that file when
teaching Codex, Claude Code, OpenCode, Cursor, or another coding agent how to run
PAI and consume its output.

## Examples

The examples are written as agent workflows, not human demos.

```bash
uv sync

cd examples/pure-python
mise run demo

cd ../fastapi
mise run demo
```

Each example produces `.pai/runs/latest/events.jsonl` and demonstrates how an
agent should inspect a run after executing normal Python code.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv build
```

Release automation uses Commitizen:

```bash
uv run cz bump
uv run cz bump --yes  # non-interactive release path
```

`cz bump` updates `pyproject.toml`, updates `CHANGELOG.md`, creates a release
commit, and tags it using `v$version`.

See [`AGENTS.md`](AGENTS.md) for repo rules and [`spec/`](spec/) for architecture
notes.

## Contributing

PAI is for agentic coding workflows. Contributions should improve the quality,
stability, or usefulness of structured program facts for agents.

Start with [`CONTRIBUTING.md`](CONTRIBUTING.md). Keep runtime code
standard-library-only.

## License

MIT. See [`LICENSE`](LICENSE).
