# Agent Response Example

This is a complete example of what an agent can get from PAI after wrapping a
normal Python command.

The exact `run_id`, `event_id`, timestamps, durations, and call counts change
on each run. The response shapes are stable.

## Program

Run a script that fails because the payload does not include `discount_rate`:

```bash
uv run pai run --summary-json python examples/pure-python/scripts/failing_order.py
```

The human terminal still shows the normal traceback, but PAI also prints a
compact machine-readable summary:

```json
{
  "schema_version": 1,
  "run_id": "20260620T201224-03fd634a",
  "command": [
    "examples/pure-python/scripts/failing_order.py"
  ],
  "cwd": "/Users/or/Projects/pai",
  "exit_code": 1,
  "duration_ms": 100,
  "event_counts": {
    "call": 3524,
    "exception": 1,
    "import": 27,
    "run_end": 1,
    "run_start": 1
  },
  "failed_tests": 0,
  "exceptions": 1,
  "top_failure": {
    "event_id": "evt_000510",
    "kind": "exception",
    "symbol": "__main__.calculate_discount",
    "exception_type": "KeyError",
    "message": "'discount_rate'"
  }
}
```

The agent now has a stable handle: `evt_000510`.

## Failure Query

```bash
uv run pai query failures
```

```json
{
  "schema_version": 1,
  "run_id": "20260620T201224-03fd634a",
  "failed_tests": [],
  "exceptions": [
    {
      "timestamp": "2026-06-20T20:12:24.078570+00:00",
      "run_id": "20260620T201224-03fd634a",
      "event_id": "evt_000510",
      "event": "exception",
      "schema_version": 1,
      "symbol": "__main__.calculate_discount",
      "file": "/Users/or/Projects/pai/examples/pure-python/scripts/failing_order.py",
      "line": 7,
      "exception_type": "KeyError",
      "message": "'discount_rate'",
      "locals_schema": {
        "payload": {
          "type": "dict",
          "keys": [
            "customer_name",
            "amount"
          ]
        },
        "amount": {
          "type": "Decimal"
        }
      }
    }
  ]
}
```

This tells the agent the failing function, file, line, exception type, and local
variable schema. Notice that PAI records dict keys, not raw values.

## Repair Context

```bash
uv run pai query repair-context --event evt_000510
```

```json
{
  "schema_version": 1,
  "run_id": "20260620T201224-03fd634a",
  "event": {
    "timestamp": "2026-06-20T20:12:24.078570+00:00",
    "run_id": "20260620T201224-03fd634a",
    "event_id": "evt_000510",
    "event": "exception",
    "schema_version": 1,
    "symbol": "__main__.calculate_discount",
    "file": "/Users/or/Projects/pai/examples/pure-python/scripts/failing_order.py",
    "line": 7,
    "exception_type": "KeyError",
    "message": "'discount_rate'",
    "locals_schema": {
      "payload": {
        "type": "dict",
        "keys": [
          "customer_name",
          "amount"
        ]
      },
      "amount": {
        "type": "Decimal"
      }
    }
  },
  "symbol": "__main__.calculate_discount",
  "related_calls": [
    {
      "timestamp": "2026-06-20T20:12:24.078493+00:00",
      "run_id": "20260620T201224-03fd634a",
      "event_id": "evt_000506",
      "event": "call",
      "schema_version": 1,
      "caller": "__main__.summarize_order",
      "callee": "__main__.calculate_discount",
      "file": "/Users/or/Projects/pai/examples/pure-python/scripts/failing_order.py",
      "line": 7,
      "duration_ms": 0
    }
  ],
  "related_tests": [],
  "recent_effects": []
}
```

From this, an agent can infer:

- `calculate_discount` expects `payload["discount_rate"]`.
- The payload shape at failure only had `customer_name` and `amount`.
- `summarize_order` called `calculate_discount`.
- No test failure or package side effect is needed to understand this bug.

The likely repair is to either include `discount_rate` in the payload or change
`calculate_discount` to handle missing discount data intentionally.

## Why This Helps Agents

Without PAI, the agent has to parse a traceback and guess which local values
mattered. With PAI, the agent can query structured execution facts:

```bash
uv run pai query status
uv run pai query failures
uv run pai query repair-context --event evt_000510
```

The agent can then patch the code and rerun the same command.
