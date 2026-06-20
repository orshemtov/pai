# PAI FastAPI Agent Workflow

This example shows how an agent can wrap a long-running FastAPI service and
inspect structured runtime facts from a real server process.

The app remains normal FastAPI code. PAI provides the agent-facing execution
layer around it:

```bash
pai run uvicorn app.main:app
```

It demonstrates:

- `run_start` when the server process boots.
- `import` events from the app, FastAPI, and uvicorn startup path.
- `call` events while requests execute application functions.
- A structured `exception` event from an uncaught background-thread failure.
- `run_end` when the server process is stopped.

FastAPI catches normal route exceptions, so this example uses
`POST /debug/thread-crash` to start a thread that raises an uncaught `KeyError`.
That maps honestly to PAI's current exception collector, which uses
`sys.excepthook` and `threading.excepthook`.

## Run

From the repo root:

```bash
uv sync
cd examples/fastapi
mise run demo
```

The demo starts uvicorn under PAI through `python -m app.serve`, waits for
readiness, sends a normal order request, triggers the background-thread
exception, requests shutdown, and prints a summary of
`.pai/runs/latest/events.jsonl`.

## Manual Agent Flow

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

Stop the server with `Ctrl-C`, then inspect structured output:

```bash
mise run events
pai bundle --run .pai/runs/latest
```

## Output

The latest run should include `run_start`, many `import` and `call` events, one
`exception` event from `crash_in_background`, and `run_end`.
