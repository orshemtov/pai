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
from typing import Any, cast

from pai.events import CallEvent
from pai.writer import EventWriter

__all__ = ["CallCollector", "install"]

ProfileCallable = Callable[[FrameType, str, Any], None]
PAI_MODULE_PREFIX = "pai."
SITECUSTOMIZE_MODULE = "sitecustomize"


def module_name(frame: FrameType) -> str:
    value = "?"
    if "__name__" in frame.f_globals:
        value = frame.f_globals["__name__"]
    if isinstance(value, str):
        return value
    return "?"


def is_pai_internal_module(name: str) -> bool:
    return name == "pai" or name.startswith(PAI_MODULE_PREFIX) or name == SITECUSTOMIZE_MODULE


def should_trace_frame(frame: FrameType) -> bool:
    if is_pai_internal_module(module_name(frame)):
        return False

    caller = frame.f_back
    if not caller:
        return True

    return not is_pai_internal_module(module_name(caller))


class CallCollector:
    """Records Python function call durations via a ``sys.setprofile`` hook."""

    def __init__(self, writer: EventWriter, original_profile: ProfileCallable | None) -> None:
        self.writer = writer
        self.original_profile = original_profile
        self.pending: dict[int, float] = {}

    def profile_hook(self, frame: FrameType, event: str, arg: Any) -> None:
        if not should_trace_frame(frame):
            if self.original_profile:
                self.original_profile(frame, event, arg)
            return

        match event:
            case "call":
                self.pending[id(frame)] = time.monotonic()

            case "return":
                start = self.pending.pop(id(frame), None)
                if start:
                    duration_ms = int((time.monotonic() - start) * 1000)

                    module = module_name(frame)
                    callee = f"{module}.{frame.f_code.co_qualname}"

                    caller_frame = frame.f_back
                    caller = "__unknown__"
                    if caller_frame:
                        caller_module = module_name(caller_frame)
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

            case _:
                pass

        if self.original_profile:
            self.original_profile(frame, event, arg)


def install(writer: EventWriter) -> None:
    """Wire a ``CallCollector`` into ``sys.setprofile`` and ``threading.setprofile``."""
    original_profile = cast(ProfileCallable | None, sys.getprofile())
    collector = CallCollector(writer=writer, original_profile=original_profile)
    sys.setprofile(collector.profile_hook)
    threading.setprofile(collector.profile_hook)
