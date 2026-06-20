# PAI — References

## Inspiration

### Zerolang
<https://github.com/vercel-labs/zerolang>

Provide structured program information for AI systems instead of forcing models to reason over
raw source code and logs. PAI applies the same philosophy to Python *runtime* behavior.

### DataDog `dd-trace-py`
<https://github.com/DataDog/dd-trace-py>

Demonstrates runtime instrumentation and bootstrap injection (`ddtrace-run`) without modifying
application code — the model for PAI's `pai run` + `PYTHONPATH`/`sitecustomize` mechanism.

### OpenTelemetry
<https://opentelemetry.io/>

Industry standard for structured traces, spans, and runtime telemetry. PAI borrows the
"structured events over text" framing, targeting agents rather than dashboards.

## CPython runtime hooks

- `site` / `sitecustomize` — startup import hook used for injection.
  <https://docs.python.org/3/library/site.html>
- `sys.excepthook` — <https://docs.python.org/3/library/sys.html#sys.excepthook>
- `threading.excepthook` — <https://docs.python.org/3/library/threading.html#threading.excepthook>
- `sys.setprofile` — <https://docs.python.org/3/library/sys.html#sys.setprofile>
- import system / `sys.meta_path` — <https://docs.python.org/3/reference/import.html>

## P5 side-effect target libraries

Reference: <https://ddtrace.readthedocs.io/en/stable/#supported-libraries> (full ddtrace matrix).

Initial targets:
- **HTTP**: `requests`, `httpx`
- **AWS**: `boto3`, `aioboto3`
- **SQL / async DB**: `sqlalchemy`, `asyncpg`, `psycopg2`

Future expansion (not yet planned):
- AI SDKs: `openai`, `anthropic`
- Cache: `redis`, `pymemcache`
- Queue: `celery`, `kombu`
- Search: `elasticsearch`, `opensearch`

Architecture: import hook detects library import, patches session/cursor/client at import time.
No runtime deps — patches use stdlib `unittest.mock`-style attribute replacement.

## Tooling

- uv — <https://docs.astral.sh/uv/>
- ruff — <https://docs.astral.sh/ruff/>
- ty — <https://github.com/astral-sh/ty>
- prek — <https://github.com/j178/prek>
- pytest — <https://docs.pytest.org/>
