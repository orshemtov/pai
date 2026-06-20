"""Launch a target command with PAI injected into its interpreter.

The runner prepends PAI's bootstrap directory to ``PYTHONPATH`` (so CPython imports
our ``sitecustomize`` at startup) and sets ``PAI_RUN_DIR`` so the injected collectors
know where to write. The target then runs as a normal subprocess.

After the subprocess exits the runner writes a ``RunEndEvent`` directly to the run dir,
recording the exit code and total duration.
"""

import os
import subprocess
import time
from collections.abc import Mapping, Sequence
from pathlib import Path

import pai.run
from pai.events import RunEndEvent
from pai.writer import EventWriter

__all__ = ["bootstrap_dir", "build_env", "run"]

RUN_DIR_ENV = "PAI_RUN_DIR"
PYTHONPATH_ENV = "PYTHONPATH"


def bootstrap_dir() -> Path:
    """Return the directory containing the injected ``sitecustomize.py``."""
    return Path(__file__).parent / "bootstrap"


def build_env(run_dir: Path, env: Mapping[str, str]) -> dict[str, str]:
    """Return a copy of ``env`` with PAI's bootstrap dir and run dir injected."""
    result = dict(env)

    bootstrap = str(bootstrap_dir())
    existing = ""
    if PYTHONPATH_ENV in result:
        existing = result[PYTHONPATH_ENV]
    if existing:
        result[PYTHONPATH_ENV] = bootstrap + os.pathsep + existing
    else:
        result[PYTHONPATH_ENV] = bootstrap

    result[RUN_DIR_ENV] = str(run_dir)
    return result


def run(
    argv: Sequence[str],
    base: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    """Run ``argv`` as a PAI-instrumented subprocess; return its exit code."""
    source_env = env or os.environ

    run_dir = pai.run.create_run_dir(base)
    injected_env = build_env(run_dir, source_env)

    start = time.monotonic()
    completed = subprocess.run(list(argv), env=injected_env, check=False)
    duration_ms = int((time.monotonic() - start) * 1000)

    with EventWriter(run_dir) as writer:
        writer.write(RunEndEvent(exit_code=completed.returncode, duration_ms=duration_ms))

    return completed.returncode
