# PAI Pure Python Example

This example shows how PAI traces ordinary Python scripts without changing the
application code. It demonstrates:

- `run_start` and `run_end` events around a target process.
- `import` events from modules imported by the script.
- `call` events for app-owned functions.
- A structured `exception` event with local variable schemas, not raw values.
- `test` events when running pytest through `pai run`.

## Run It

Install/sync the workspace from the repo root first:

```bash
uv sync
```

Then run the scripted demo:

```bash
cd examples/pure-python
mise run demo
```

The demo runs one successful script and one failing script, then prints a compact
summary of `.pai/runs/latest/events.jsonl`.

## Useful Commands

```bash
mise run run:success
mise run run:failure
mise run run:tests
mise run events
```

The failure command exits non-zero on purpose. It raises a `KeyError` because
`scripts/failing_order.py` reads a missing `discount_rate` key. PAI records the
exception type, symbol, line, and the schema of local variables such as:

```json
{"payload": {"type": "dict", "keys": ["customer_name", "amount"]}}
```

Notice that the event includes keys and types, but not user values.

The pytest command also exits non-zero on purpose. One test has an intentionally
wrong expected total so PAI can emit a failed `test` event with the pytest failure
message.

## Inspect the Output

PAI writes events under:

```text
.pai/runs/latest/events.jsonl
```

Each line is one JSON event. The latest run should include `run_start`, `import`,
`call`, `exception`, and `run_end` for the failing script.
