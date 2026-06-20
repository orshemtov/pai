# PAI FastAPI Example

This example shows PAI wrapping a long-running FastAPI service with:

```bash
pai run uvicorn app.main:app
```

It demonstrates:

- `run_start` when the server process boots.
- `import` events from the app, FastAPI, and uvicorn startup path.
- `call` events while requests execute application functions.
- A structured `exception` event from an uncaught background-thread failure.
- `run_end` when the server process is stopped.

FastAPI catches normal route exceptions, so this example uses a
`POST /debug/thread-crash` endpoint to start a thread that raises an uncaught
`KeyError`. That maps honestly to PAI's current exception collector, which uses
`sys.excepthook` and `threading.excepthook`.

## Run It

Install/sync the workspace from the repo root first:

```bash
uv sync
```

Then run the scripted demo:

```bash
cd examples/fastapi
mise run demo
```

The demo starts uvicorn under PAI through `python -m app.serve`, waits for
readiness, sends a normal order request, triggers the background-thread exception,
requests shutdown, and prints a summary of `.pai/runs/latest/events.jsonl`.

## Manual Flow

In one terminal:

```bash
cd examples/fastapi
mise run serve
```

In another terminal:

```bash
cd examples/fastapi
mise run health
curl http://127.0.0.1:8765/orders/100
curl -X POST http://127.0.0.1:8765/debug/thread-crash
```

Stop the server with `Ctrl-C`, then inspect the latest run:

```bash
mise run events
```

## Inspect the Output

PAI writes events under:

```text
.pai/runs/latest/events.jsonl
```

The scripted demo should include `run_start`, many `import` and `call` events, one
`exception` event from `crash_in_background`, and `run_end`.
