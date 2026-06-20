"""PAI pytest plugin — emits ``TestEvent`` for each test item.

Activated automatically when PAI_RUN_DIR is set in the environment (i.e. the
test suite is running under ``pai run``). No-op otherwise, so installing PAI
never breaks a plain ``pytest`` invocation.

Registered as a pytest entry-point in ``pyproject.toml`` under ``[project.entry-points.pytest11]``.
"""

import os
import time
from pathlib import Path

import pytest

from pai.events import TestEvent
from pai.writer import EventWriter

RUN_DIR_ENV = "PAI_RUN_DIR"


class PaiPlugin:
    """Pytest plugin that writes one ``TestEvent`` per test to the PAI run dir."""

    def __init__(self, run_dir: Path) -> None:
        self.writer = EventWriter(run_dir)
        self.start_times: dict[str, float] = {}

    @pytest.hookimpl
    def pytest_runtest_logstart(self, nodeid: str, location: tuple[str, int | None, str]) -> None:
        self.start_times[nodeid] = time.monotonic()

    @pytest.hookimpl
    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when != "call":
            return

        start = self.start_times.pop(report.nodeid, time.monotonic())
        duration_ms = int((time.monotonic() - start) * 1000)

        outcome = "passed"
        if report.failed:
            outcome = "failed"
        elif report.skipped:
            outcome = "skipped"

        message = ""
        if report.failed and report.longrepr:
            message = str(report.longrepr)

        file = ""
        if report.location:
            file = report.location[0]

        self.writer.write(
            TestEvent(
                test_id=report.nodeid,
                outcome=outcome,
                duration_ms=duration_ms,
                file=file,
                message=message,
            )
        )

    @pytest.hookimpl
    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int) -> None:
        self.writer.close()


def pytest_configure(config: pytest.Config) -> None:
    run_dir_str = os.environ.get(RUN_DIR_ENV)
    if not run_dir_str:
        return
    config.pluginmanager.register(PaiPlugin(run_dir=Path(run_dir_str)))
