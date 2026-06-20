"""Thread-safe sink that serializes events to JSONL.

Every event is appended to ``events.jsonl``. For convenience each event is also
fanned out to a per-type file (e.g. ``exceptions.json``) consumed by bundles.
"""

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import TextIO

from pai.events import Event

__all__ = ["EventWriter"]

EVENTS_FILE = "events.jsonl"


class EventWriter:
    """Append events to a run directory. Safe to call from multiple threads."""

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.lock = threading.RLock()
        self.next_event_number = 1

        self.events_file = self.open_file(EVENTS_FILE)
        self.type_files: dict[str, TextIO] = {}

    def write(self, event: Event) -> None:
        with self.lock:
            event_id = f"evt_{self.next_event_number:06d}"
            self.next_event_number += 1

            data: dict = {
                "timestamp": datetime.now(UTC).isoformat(),
                "run_id": self.run_dir.name,
                "event_id": event_id,
            }
            data.update(event.to_dict())

            line = json.dumps(data)
            self.append_line(self.events_file, line)
            self.append_line(self.type_file_for(event.event_name), line)

    def close(self) -> None:
        with self.lock:
            self.events_file.close()
            for handle in self.type_files.values():
                handle.close()
            self.type_files.clear()

    def __enter__(self) -> "EventWriter":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def open_file(self, name: str) -> TextIO:
        return (self.run_dir / name).open("a", encoding="utf-8")

    def type_file_for(self, event_name: str) -> TextIO:
        handle = None
        if event_name in self.type_files:
            handle = self.type_files[event_name]
        if not handle:
            handle = self.open_file(f"{event_name}s.json")
            self.type_files[event_name] = handle
        return handle

    def append_line(self, handle: TextIO, line: str) -> None:
        handle.write(line)
        handle.write("\n")
        handle.flush()
