# AGENTS.md — Rules for coding agents

Guidelines for any agent (or human) writing code in this repo. Read `spec/` first:
`OVERVIEW.md` (what/why), `ARCHITECTURE.md` (how), `PHASES.md` / `TASKS.md` (plan).

> `pai` = **Python AI** ("Paithon" / "pAIthon").

## Golden rule: zero runtime dependencies

PAI is injected into the **target** process via `sitecustomize`. Anything imported on the
runtime path (`pai.bootstrap`, `pai.collectors`, `pai.events`, `pai.writer`, `pai.run`) must
use the **standard library only**. Do not add runtime dependencies to `[project.dependencies]`.
Dev tooling goes in the dev dependency group.

## Coding standards

- **Modern typing.** Annotate everything. Use `@dataclass` for records. Use `TypedDict` for
  known-shape dicts (prefer a dataclass when the shape is owned by us).
- **Owned records use dataclasses.** If we own the shape and it has behavior or crosses function
  boundaries, prefer a dataclass over a plain dict. Use plain dicts for parsed/emitted JSON and
  genuinely dynamic mappings.
- **Use `StrEnum` for string domains.** Event names, command names, modes, and other finite
  string sets should use `enum.StrEnum` instead of loose string constants when practical.
- **Prefer `match` for command/type dispatch.** Use `match` over long `if` / `elif` chains when
  dispatching on a finite domain such as a command or event type.
- **Loops over comprehensions.** Write normal `for` loops for readability. Avoid list/dict/set
  comprehensions and generator expressions except trivial one-liners that are clearer that way.
- **Truthiness over sentinel spelling.** Prefer `if value:` and `if not value:` over
  `is None` / `is not None` checks when the value's truthiness represents presence. If an
  empty collection, zero, or empty string is a valid distinct value, make that distinction
  explicit with a small helper or clear branch structure.
- **No `hasattr` / `getattr` / `setattr`.** Use explicit attribute access and typed structures.
- **No `.get(...)` for field access.** Avoid `dict.get`, `Mapping.get`, and default-value field
  reads. Use dataclasses or typed structures when we own the shape. For parsed JSON or external
  mappings, validate required keys with direct `mapping[key]` access and use explicit
  `"key" in mapping` branches for optional fields.
- **No `from __future__ import annotations`.**
- **Imports at the top only.** No mid-file or in-function imports.
- **Avoid import aliases.** Prefer importing the real name. Use an alias only when it avoids a
  genuine name collision or follows a standard convention that makes code clearer.
- **Avoid import cycles.** Keep module dependencies directed. Runtime-injected modules must not
  import CLI/query/bundle/dev-only modules.
- **Keep `__init__.py` logic-free.** Use `__init__.py` only as a package marker or explicit
  `__all__` / re-export surface. Put install hooks, registries, dispatch, and behavior in
  normal modules.
- **One effect per line.** Avoid semicolon-style command/code chains and dense one-liners that
  import, compute, call, and print together. Split setup, action, and output into separate
  statements so execution is easy to read and debug.
- **Dependency injection — no implicit global access.** Functions must not read mutable
  globals (env vars, `sys.path`, `sys.excepthook`, etc.) from outer or global scope. Pass them
  as parameters from the caller. Module-level constants (ALL_CAPS) are fine. `os.environ` as a
  default at a public API boundary (`env: Mapping | None = None`, fall back in body) is
  acceptable — internal helpers must receive the resolved value, not re-read it. For hooks that
  capture state, use a class that holds injected deps as attributes rather than closures.
- **No `_` prefix on anything.** Do not use underscore-prefixed names for modules, functions,
  methods, attributes, or constants. Control the public API solely through `__all__` and what
  `__init__.py` re-exports — not naming. (Dunder methods like `__init__` are unaffected.)
- **File size ≤ 500 lines.** Split by cohesion into more modules (files/folders) when growing.
- **Spacing tells a story.** Separate logical blocks with blank lines following the author's
  chain of thought; group related statements.
- **Imperative, simple, idiomatic.** No unnecessary abstractions, no speculative generality.
  Straightforward code beats clever code.

## TDD workflow

1. Write the failing test that encodes the desired behavior (see `tests/`).
2. Write the minimal code to pass it.
3. Make ruff + ty clean.
4. Refactor if needed; keep tests green.

Tests describe behavior precisely — they are the spec for each unit.

## Pytest conventions

- Put shared test setup in `tests/conftest.py` fixtures instead of repeating path, command, or
  parsing helpers across test modules.
- Keep test bodies focused on behavior. Fixtures should provide environment/context; tests
  should arrange only the inputs that are specific to the behavior under test.
- Prefer real subprocesses and files for integration behavior. Avoid inline `python -c` snippets
  when a small script or fixture is clearer.

## Privacy of captured data

Collectors record **schemas, not values**: variable types and dict keys, never raw values.
Never serialize user data into events.

## Commands

```bash
uv sync                       # install deps (incl. dev group)
uv run pytest                 # run tests
uv run ruff check .           # lint
uv run ruff format .          # format (use --check in CI)
uv run ty check               # type check
uv run lint-imports           # import architecture contracts
prek run --all-files          # all pre-commit hooks
```

## Conventions ruff enforces

`E402` (import not at top), `PLC0415` (import outside top level), `UP` (pyupgrade / modern
syntax), `B009`/`B010` (constant get/set-attr). The non-enforceable rules above (comprehension
avoidance, 500-line cap, no `_` prefixes, no future annotations) are checked in review.
