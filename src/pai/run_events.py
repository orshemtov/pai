"""Run-event loading and filtering."""

from dataclasses import dataclass
from pathlib import Path

from pai.bundle import load_events
from pai.event_names import EventName, is_side_effect_event
from pai.event_records import EventRecord, event_id_for, required_text

__all__ = ["RunEvents", "load_run_events"]


@dataclass
class RunEvents:
    run_dir: Path
    events: list[dict]

    @property
    def run_id(self) -> str:
        if self.run_dir.exists():
            return self.run_dir.resolve().name
        return self.run_dir.name

    @property
    def run_start(self) -> dict | None:
        return self.first_event(EventName.RUN_START)

    @property
    def run_end(self) -> dict | None:
        return self.first_event(EventName.RUN_END)

    @property
    def tests(self) -> list[dict]:
        return self.events_named(EventName.TEST)

    @property
    def failed_tests(self) -> list[dict]:
        result: list[dict] = []
        for event in self.tests:
            if required_text(event, "outcome") == "failed":
                result.append(event)
        return result

    @property
    def exceptions(self) -> list[dict]:
        return self.events_named(EventName.EXCEPTION)

    @property
    def effects_by_package(self) -> dict[str, list[dict]]:
        result: dict[str, list[dict]] = {}
        for event in self.events:
            event_name = EventRecord(event).name
            match event_name:
                case EventName() if is_side_effect_event(event_name):
                    events_for_package = result.setdefault(event_name.value, [])
                    events_for_package.append(event)
                case _:
                    continue
        return result

    def first_event(self, event_name: EventName) -> dict | None:
        for event in self.events:
            match EventRecord(event).name:
                case name if name == event_name:
                    return event
                case _:
                    continue
        return None

    def events_named(self, event_name: EventName) -> list[dict]:
        result: list[dict] = []
        for event in self.events:
            match EventRecord(event).name:
                case name if name == event_name:
                    result.append(event)
                case _:
                    continue
        return result

    def event_by_id(self, event_id: str) -> dict:
        for event in self.events:
            if event_id_for(event) == event_id:
                return event
        return {}


def load_run_events(run_dir: Path) -> RunEvents:
    return RunEvents(run_dir=run_dir, events=load_events(run_dir))
