---
name: pai
description: Use PAI to run Python programs and inspect agent-native JSON runtime facts instead of scraping terminal output.
---

# PAI Agent Workflow

PAI is an agent-facing execution layer for Python. Humans keep writing ordinary
Python; agents use PAI to receive structured runtime facts instead of scraping
tracebacks, pytest prose, logs, and command output.

## When To Use PAI

Use PAI when:

- A Python command fails and the traceback is not enough context.
- You need structured pytest results for an agent workflow.
- You need to inspect runtime imports or app-owned calls.
- You want an agent-readable bundle from a script, test run, or web server run.

Do not use PAI as a production APM or profiler. Its purpose is to give coding
agents better program output.

## Install

From a checkout:

```bash
git clone https://github.com/orshemtov/pai.git
cd pai
uv sync
```

The planned PyPI distribution is `pai-trace`. The CLI command and Python import
package are named `pai`.

## Run A Program

Wrap the target command with `pai run`:

```bash
pai run python app.py
pai run pytest
pai run uvicorn app.main:app
```

PAI returns the same exit code as the target command. A non-zero exit can still
be useful because the run directory may contain structured exception or test
events.

## Inspect Events

PAI writes newline-delimited JSON to:

```text
.pai/runs/latest/events.jsonl
```

Read that file directly when you need event-level detail. Prefer structured JSON
over terminal output. Treat terminal output as a fallback for facts PAI does not
yet expose.

Important event families:

- `run_start` and `run_end`: command, cwd, Python version, exit code, duration.
- `exception`: symbol, file, line, exception type, message, local schemas.
- `import`: runtime import edges.
- `call`: app-owned function call timing.
- `test`: pytest item outcome, duration, file, message.
- `http`, `sql`, `aws`, `ai`: side-effect event families.

## Build A Bundle

Use `pai bundle` when you need one JSON artifact for agent context:

```bash
pai bundle --run .pai/runs/latest
pai bundle --run .pai/runs/latest --out pai-bundle.json
```

The bundle groups events into top-level sections:

```text
run, exceptions, imports, calls, tests, http, sql, aws, ai
```

## Privacy Rules

PAI captures schemas, not values. Exception locals record type names and dict
keys only. Do not ask PAI to serialize user data into events.

Runtime-injected code must stay standard-library-only. Do not add runtime
dependencies to the target process path.

## Troubleshooting

If `.pai/runs/latest` does not exist:

- Confirm the command was run through `pai run`.
- Confirm the target process was Python.
- Check whether the command ran from a different working directory.

If `pai run pytest` does not emit test events:

- Confirm `PAI_RUN_DIR` is set by `pai run`.
- Confirm the installed package exposes the `pai.pytest_plugin` pytest entry
  point.
- Use `pai bundle --run .pai/runs/latest` to check whether events were emitted
  but not obvious in terminal output.

If the target command fails:

- Preserve the target exit code.
- Inspect `exception` and `test` events before reading raw terminal output.
- Use `run_end.exit_code` to distinguish target failure from collection output.
