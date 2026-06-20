import json
import sys
from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def pure_python_example(repo_root: Path) -> Path:
    return repo_root / "examples" / "pure-python"


@pytest.fixture
def fastapi_example(repo_root: Path) -> Path:
    return repo_root / "examples" / "fastapi"


@pytest.fixture
def pai_command() -> Path:
    command = Path(sys.executable).parent / "pai"
    assert command.exists()
    return command


def read_jsonl(path: Path) -> list[dict]:
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        events.append(json.loads(line))
    return events


@pytest.fixture
def read_events() -> Callable[[Path], list[dict]]:
    return read_jsonl
