"""Collector for Python function calls via the ``sys.setprofile`` hook.

On each ``call`` event the frame id and start time are recorded. On ``return``,
duration is computed and a ``CallEvent`` is emitted. C extensions are skipped —
their calls fire ``c_call``/``c_return``, which are not traced here.

``sys.setprofile`` disables re-entry while the hook is executing, so there is no
risk of recursive emission from within the hook itself.
"""

import sys
import threading
import time
from collections.abc import Callable
from types import FrameType
from typing import Any

from pai.events import CallEvent
from pai.writer import EventWriter

__all__ = ["CallCollector", "install"]

ProfileCallable = Callable[[FrameType, str, Any], None]


class CallCollector:
    """Records Python function call durations via a ``sys.setprofile`` hook."""

    def __init__(self, writer: EventWriter, original_profile: ProfileCallable | None) -> None:
        self.writer = writer
        self.original_profile = original_profile
        self.pending: dict[int, float] = {}

    def profile_hook(self, frame: FrameType, event: str, arg: Any) -> None:
        if event == "call":
            self.pending[id(frame)] = time.monotonic()

        elif event == "return":
            start = self.pending.pop(id(frame), None)
            if start is not None:
                duration_ms = int((time.monotonic() - start) * 1000)

                module = frame.f_globals.get("__name__", "?")
                callee = f"{module}.{frame.f_code.co_qualname}"

                caller_frame = frame.f_back
                caller = "__unknown__"
                if caller_frame is not None:
                    caller_module = caller_frame.f_globals.get("__name__", "?")
                    caller = f"{caller_module}.{caller_frame.f_code.co_qualname}"

                self.writer.write(
                    CallEvent(
                        caller=caller,
                        callee=callee,
                        file=frame.f_code.co_filename,
                        line=frame.f_lineno,
                        duration_ms=duration_ms,
                    )
                )

        if self.original_profile is not None:
            self.original_profile(frame, event, arg)


def install(writer: EventWriter) -> None:
    """Wire a ``CallCollector`` into ``sys.setprofile`` and ``threading.setprofile``."""
    collector = CallCollector(writer=writer, original_profile=sys.getprofile())  # type: ignore
    sys.setprofile(collector.profile_hook)
    threading.setprofile(collector.profile_hook)
