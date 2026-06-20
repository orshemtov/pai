# Contributing

Thanks for working on PAI.

Start by reading [`AGENTS.md`](AGENTS.md) and the files in [`spec/`](spec/). They
define the product, architecture, and coding rules.

## Setup

```bash
uv sync
```

## Checks

Run the same checks before opening a pull request:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
```

## Commits And Changelog

Use Conventional Commit messages. Commitizen is installed in the dev dependency
group:

```bash
uv run cz commit
uv run cz bump
uv run cz bump --yes  # non-interactive release path
```

`cz bump` updates the project version, updates `CHANGELOG.md`, creates a release
commit, and creates a `v$version` tag.

Install commit hooks with:

```bash
prek install
prek install --hook-type commit-msg --hook-type pre-push
```

## Development Rules

- Keep runtime-injected modules standard-library-only.
- Add tests before behavior changes.
- Keep captured data private: record schemas and metadata, not raw values.
- Preserve the `pai run <cmd>` contract: target exit code is returned unchanged.
- Keep files focused and under the repo's 500-line limit.

## Pull Requests

Include:

- The behavior changed.
- The tests added or updated.
- The commands you ran and their results.
