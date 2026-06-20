# PAI — Overview

> `pai` = **Python AI** ("Paithon" / "pAIthon").

## What

PAI is a Python runtime wrapper that exposes structured execution data for coding agents.

You run your program through it — `pai run python app.py`, `pai run pytest` — and PAI
injects runtime hooks into the process and writes **machine-readable events** describing what
happened: exceptions, calls, imports, tests, side effects. No code changes, no new framework.

> PAI is to Python what OpenTelemetry is to observability: a structured runtime layer — but
> designed for coding agents instead of dashboards.

## Why

Today's coding agents spend significant effort extracting information from artifacts designed
for humans: tracebacks, test output, console logs, coverage reports, runtime behavior,
dependency graphs.

PAI exposes the same information as structured data so agents can reason directly about
programs, instead of scraping terminal text.

Instead of:

```text
KeyError: 'user_id'
  File "main.py", line 42...
```

an agent receives:

```json
{
  "event": "exception",
  "symbol": "main.parse_user",
  "exception_type": "KeyError",
  "message": "'user_id'"
}
```

## Vision

PAI turns Python execution into a queryable graph of symbols, calls, tests, failures, and
side effects. Agents consume structured facts, not blobs of text.

## Features

The feature set below is the long-term target. See `PHASES.md` for what ships in the MVP
versus what is deferred.

### Structured exceptions
Convert Python exceptions into structured events with symbol, location, and a **schema** of
local variables (types and dict keys only — never raw values).

```json
{
  "event": "exception",
  "symbol": "main.parse_user",
  "file": "main.py",
  "line": 2,
  "exception_type": "KeyError",
  "message": "'user_id'",
  "locals_schema": { "payload": { "type": "dict", "keys": ["name"] } }
}
```

### Test intelligence
Link failing tests to the code they executed.

```json
{
  "event": "test_failure",
  "test": "tests/test_orders.py::test_create_order",
  "covered_functions": ["app.orders.create_order", "app.validation.validate_payload"]
}
```

### Import graph
Discover module dependencies automatically.

### Symbol graph
Map functions, classes, and references (who calls whom).

### Runtime call tracing
Capture execution flow and timing between symbols.

### Side-effect tracing
Track interactions with external systems (HTTP, SQL).

### Structured logging
Convert log records into machine-readable events with their `extra` fields.

### Request tracing
Understand a complete web request's execution (route → handler → calls → queries).

### Agent context bundles
Package a run into a directory agents can consume:

```text
.pai/runs/latest/
├── events.jsonl
├── imports.json
├── symbols.json
├── tests.json
└── exceptions.json
```

## Non-goals

- Not a profiler or APM dashboard for humans.
- Not a replacement for OpenTelemetry in production observability.
- Not a new language or framework — existing Python projects run unmodified.
