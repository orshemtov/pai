"""Run identity and on-disk layout.

A run owns a directory ``<base>/.pai/runs/<run-id>/`` where collectors write events.
A ``latest`` pointer in the runs root always references the most recent run.
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path

__all__ = ["create_run_dir", "latest_pointer", "new_run_id", "runs_root"]

PAI_DIR_NAME = ".pai"
RUNS_DIR_NAME = "runs"
LATEST_NAME = "latest"

TIMESTAMP_FORMAT = "%Y%m%dT%H%M%S"


def new_run_id() -> str:
    """Return a sortable, unique run id: ``<utc-timestamp>-<short-uuid>``."""
    timestamp = datetime.now(UTC).strftime(TIMESTAMP_FORMAT)
    suffix = uuid.uuid4().hex[:8]
    return f"{timestamp}-{suffix}"


def runs_root(base: Path | None = None) -> Path:
    """Return the directory holding all runs for ``base`` (defaults to cwd)."""
    root = base if base is not None else Path.cwd()
    return root / PAI_DIR_NAME / RUNS_DIR_NAME


def latest_pointer(base: Path | None = None) -> Path:
    """Return the path of the ``latest`` symlink in the runs root."""
    return runs_root(base) / LATEST_NAME


def create_run_dir(base: Path | None = None) -> Path:
    """Create a fresh run directory and repoint ``latest`` at it."""
    run_dir = runs_root(base) / new_run_id()
    run_dir.mkdir(parents=True, exist_ok=True)

    pointer = latest_pointer(base)
    if pointer.is_symlink() or pointer.exists():
        pointer.unlink()
    pointer.symlink_to(run_dir.name)

    return run_dir
