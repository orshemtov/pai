import re
from pathlib import Path

from pai import run

RUN_ID_PATTERN = re.compile(r"^\d{8}T\d{6}-[0-9a-f]{8}$")


def test_new_run_id_matches_format() -> None:
    run_id = run.new_run_id()

    assert RUN_ID_PATTERN.match(run_id)


def test_new_run_id_is_unique() -> None:
    ids: set[str] = set()
    for _ in range(50):
        ids.add(run.new_run_id())

    assert len(ids) == 50


def test_create_run_dir_creates_directory_under_runs_root(tmp_path: Path) -> None:
    run_dir = run.create_run_dir(base=tmp_path)

    assert run_dir.is_dir()
    assert run_dir.parent == run.runs_root(base=tmp_path)


def test_create_run_dir_updates_latest_pointer(tmp_path: Path) -> None:
    run_dir = run.create_run_dir(base=tmp_path)

    latest = run.latest_pointer(base=tmp_path)

    assert latest.resolve() == run_dir.resolve()
