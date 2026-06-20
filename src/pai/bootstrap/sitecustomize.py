"""Injected interpreter-startup hook.

PAI's runner prepends this directory to ``PYTHONPATH``, so CPython imports this module
automatically at startup. We chain any pre-existing ``sitecustomize`` (so we don't clobber
the target's own startup customization), then install collectors when ``PAI_RUN_DIR`` is set.

Dependencies (env, sys.path) are injected into helpers rather than read from global scope.
Everything is wrapped defensively: instrumentation must never break the target process.
"""

import contextlib
import os
import runpy
import sys
from collections.abc import Mapping
from pathlib import Path

from pai.collectors import calls, exceptions, imports
from pai.events import RunStartEvent
from pai.writer import EventWriter

RUN_DIR_ENV = "PAI_RUN_DIR"


def chain_existing_sitecustomize(search_path: list[str]) -> None:
    this_dir = os.path.dirname(os.path.abspath(__file__))

    for entry in search_path:
        entry_dir = os.path.abspath(entry)
        if entry_dir == this_dir:
            continue

        candidate = os.path.join(entry_dir, "sitecustomize.py")
        if os.path.isfile(candidate):
            runpy.run_path(candidate, run_name="sitecustomize")
            return


def activate(env: Mapping[str, str], argv: list[str], cwd: str, python_version: str) -> None:
    run_dir = env.get(RUN_DIR_ENV)
    if not run_dir:
        return

    writer = EventWriter(Path(run_dir))

    writer.write(RunStartEvent(command=argv, cwd=cwd, python_version=python_version))

    exceptions.install(writer)
    imports.install(writer)
    calls.install(writer)


with contextlib.suppress(Exception):
    chain_existing_sitecustomize(list(sys.path))

with contextlib.suppress(Exception):
    activate(
        env=os.environ,
        argv=list(sys.argv),
        cwd=os.getcwd(),
        python_version=sys.version,
    )
