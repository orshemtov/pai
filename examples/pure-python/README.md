# PAI Pure Python Agent Workflow

This example shows how an agent can run ordinary Python scripts and inspect
structured runtime facts instead of terminal prose.

It demonstrates:

- `run_start` and `run_end` events around a target process.
- `import` events from modules imported by the script.
- `call` events for app-owned functions.
- A structured `exception` event with local variable schemas, not raw values.
- `test` events when pytest is run through `pai run`.

## Run

From the repo root:

```bash
uv sync
cd examples/pure-python
mise run demo
```

The demo runs one successful script and one failing script, then prints a compact
summary of `.pai/runs/latest/events.jsonl`.

## Agent Commands

```bash
mise run run:success
mise run run:failure
mise run run:tests
mise run events
```

The failure command exits non-zero on purpose. It raises a `KeyError` because
`scripts/failing_order.py` reads a missing `discount_rate` key. Agents should
inspect the emitted `exception` event before falling back to traceback text.

PAI records shape, not user data:

```json
{
  "payload": {
    "type": "dict",
    "keys": ["amount", "customer_name"]
  }
}
```

The pytest command also exits non-zero on purpose. One test has an intentionally
wrong expected total so PAI can emit a failed `test` event with the pytest
failure message.

The pytest task sets `PYTHONPATH=.` because this example is a workspace member,
and pytest otherwise resolves imports from the workspace root instead of the
example directory.

## Output

PAI writes events under:

```text
.pai/runs/latest/events.jsonl
```

An agent should read the JSON events or run:

```bash
pai bundle --run .pai/runs/latest
```
