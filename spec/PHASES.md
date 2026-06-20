# PAI — Phases

High-level milestone view. The MVP proves the full pipeline end-to-end with one collector;
later phases layer features onto the same pipeline. Detailed task breakdown lives in
`TASKS.md`.

## MVP

### Phase 0 — Spec + SDLC
- Spec docs (`OVERVIEW`, `ARCHITECTURE`, `REFERENCES`, `TASKS`, `PHASES`).
- `AGENTS.md` coding standards.
- Tooling: uv dev group, ruff, ty, pytest, prek, `.gitignore`.

### Phase 1 — Core pipeline + exceptions
- `pai run <cmd>`: run-dir lifecycle, env injection (`PYTHONPATH` + `PAI_RUN_DIR`), subprocess.
- Injected `bootstrap/sitecustomize.py` (chains any pre-existing sitecustomize).
- `EventWriter`: thread-safe JSONL append + per-type fan-out.
- Event dataclasses (`ExceptionEvent`).
- Exception collector: `sys.excepthook` + `threading.excepthook` → structured event with
  `locals_schema` (types/dict-keys only).
- End-to-end: reproduces idea-doc **Example 1** (KeyError → structured event in `events.jsonl`).

**MVP done when:** `pai run python <script that raises>` yields a structured exception event,
all tests green, ruff + ty + prek clean.

## Deferred

| Phase | Feature | Mechanism |
|-------|---------|-----------|
| P2 | Import graph | `ast` static analysis + import hooks |
| P3 | Runtime call tracing + timing | `sys.setprofile` |
| P4 | Test intelligence (failures ↔ covered code) | pytest plugin |
| P5 | Side-effect tracing (HTTP, SQL) + framework integrations | conditional monkeypatch on import |
| P6 | `pai bundle` + symbol graph | aggregate run dir into agent bundle |

Deferred work must not require reworking the Phase 1 pipeline — new collectors register with
the same writer and run-dir contract.
