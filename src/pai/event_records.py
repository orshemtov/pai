"""Typed accessors for parsed JSON event records."""

from dataclasses import dataclass

from pai.event_names import EventName, event_name_from

__all__ = [
    "EventRecord",
    "event_id_for",
    "event_type_text",
    "optional_text",
    "required_text",
]


@dataclass
class EventRecord:
    """A parsed event JSON object with explicit field access."""

    data: dict

    @property
    def name(self) -> EventName | None:
        if "event" not in self.data:
            return None
        return event_name_from(self.data["event"])

    @property
    def name_text(self) -> str:
        name = self.name
        match name:
            case EventName():
                return name.value
            case None:
                if "event" not in self.data:
                    return "unknown"
                return str(self.data["event"])

    @property
    def event_id(self) -> str:
        if "event_id" not in self.data:
            return ""
        return str(self.data["event_id"])

    def required_text(self, field: str) -> str:
        value = self.data[field]
        return str(value)

    def optional_text(self, field: str) -> str:
        if field not in self.data:
            return ""
        return str(self.data[field])


def event_id_for(event: dict) -> str:
    return EventRecord(event).event_id


def event_type_text(event: dict) -> str:
    return EventRecord(event).name_text


def required_text(event: dict, field: str) -> str:
    return EventRecord(event).required_text(field)


def optional_text(event: dict, field: str) -> str:
    return EventRecord(event).optional_text(field)
