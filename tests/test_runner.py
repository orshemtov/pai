import os
from pathlib import Path

from pai import runner


def test_bootstrap_dir_contains_sitecustomize() -> None:
    bootstrap = runner.bootstrap_dir()

    assert (bootstrap / "sitecustomize.py").is_file()


def test_build_env_injects_bootstrap_and_run_dir(tmp_path: Path) -> None:
    env = runner.build_env(tmp_path, env={})

    pythonpath = env["PYTHONPATH"]

    assert pythonpath == str(runner.bootstrap_dir())
    assert env["PAI_RUN_DIR"] == str(tmp_path)


def test_build_env_preserves_existing_pythonpath(tmp_path: Path) -> None:
    env = runner.build_env(tmp_path, env={"PYTHONPATH": "/foo"})

    expected = str(runner.bootstrap_dir()) + os.pathsep + "/foo"

    assert env["PYTHONPATH"] == expected
