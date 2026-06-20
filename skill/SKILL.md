---
name: pai
description: Use PAI when working on Python code and an agent needs structured runtime facts from scripts, pytest, web servers, or failing commands instead of scraping tracebacks, logs, pytest prose, or terminal output. Trigger for debugging Python failures, collecting test outcomes, inspecting exceptions and local schemas, understanding runtime imports/calls, checking package side effects such as requests/httpx/sqlalchemy/boto3/openai, or building an agent-readable execution bundle.
---

# PAI

PAI wraps normal Python commands and writes agent-native JSON about what happened.
Use it as the first debugging interface before reading raw terminal text.

## Core Loop

Run the target through PAI:

```bash
pai run --summary-json pytest
pai run --summary-json python app.py
pai run --summary-json uvicorn app.main:app
```

Then inspect the latest run from narrow to broad:

```bash
pai query status
pai query failures
pai query repair-context --event <event_id>
```

Use the `event_id` from `status.top_failure` or `failures` as the repair-context
handle. Patch the code, rerun the same `pai run ...` command, and compare the new
status.

## Query Commands

Prefer compact queries before loading full logs:

```bash
pai query status                         # exit code, counts, top failure
pai query failures                       # failed tests and uncaught exceptions
pai query tests                          # pytest outcomes
pai query effects                        # side effects grouped by package
pai query symbol --name app.parse_user   # events touching one symbol
pai query timeline --limit 50            # first N events
pai query repair-context --event evt_... # focused facts for one failure
```

Use `pai bundle --run .pai/runs/latest` only when a single full JSON artifact is
more useful than targeted queries.

## Reading Results

Trust structured fields over terminal prose:

- `run_start` / `run_end`: command, cwd, Python version, exit code, duration.
- `test`: pytest item, outcome, duration, file, message.
- `exception`: failing symbol, file, line, exception type, message, local schemas.
- `import`: runtime import edges.
- `call`: app-owned function calls and durations.
- `requests`, `httpx`, `sqlalchemy`, `asyncpg`, `boto3`, `aiobotocore`,
  `openai`, `anthropic`: concrete package side-effect events.

Every event includes `run_id`, `event_id`, and `timestamp`. Use `event_id` for
follow-up queries instead of reloading `.pai/runs/latest/events.jsonl`.

## Repair Heuristics

For exceptions:

1. Read `status.top_failure`.
2. Query `repair-context` for that event.
3. Use `event.symbol`, `file`, `line`, `exception_type`, and `locals_schema` to
   identify the broken assumption.
4. Check `related_calls` to see which code path reached the failure.

For tests:

1. Run `pai run --summary-json pytest`.
2. Query `pai query failures`.
3. Use each failed test's `test_id`, `file`, and `message` to patch the smallest
   behavior.
4. Rerun the same test command through PAI.

For side effects:

1. Query `pai query effects`.
2. Inspect concrete package groups such as `requests`, `sqlalchemy`, or `openai`.
3. Use method, URL, SQL operation, service operation, model, token counts, and
   duration fields to understand what the program actually did.

## Privacy Contract

PAI records schemas, not raw values. Exception locals include type names and dict
keys, not user data. Do not ask PAI to serialize private values into events.

## Troubleshooting

If `.pai/runs/latest` is missing, rerun the command with `pai run`.

If pytest events are missing, confirm the command was run through PAI and the
environment has the `pai.pytest_plugin` entry point installed.

If a command exits non-zero, treat that as the target command's exit code. Inspect
`run_end.exit_code`, `exception`, and `test` events before assuming PAI failed.
