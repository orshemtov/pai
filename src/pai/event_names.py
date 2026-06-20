"""Known PAI event names and event-name classification."""

from enum import StrEnum

__all__ = ["EventName", "event_name_from", "is_side_effect_event"]


class EventName(StrEnum):
    RUN_START = "run_start"
    RUN_END = "run_end"
    EXCEPTION = "exception"
    IMPORT = "import"
    CALL = "call"
    TEST = "test"

    # Side-effect package events.
    REQUESTS = "requests"
    HTTPX = "httpx"
    SQLALCHEMY = "sqlalchemy"
    ASYNCPG = "asyncpg"
    BOTO3 = "boto3"
    AIOBOTOCORE = "aiobotocore"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


def event_name_from(value: object) -> EventName | None:
    """Parse a JSON event name into a known event enum."""
    try:
        return EventName(str(value))
    except ValueError:
        return None


def is_side_effect_event(event_name: EventName) -> bool:
    """Return whether ``event_name`` represents a concrete package side effect."""
    match event_name:
        case (
            EventName.REQUESTS
            | EventName.HTTPX
            | EventName.SQLALCHEMY
            | EventName.ASYNCPG
            | EventName.BOTO3
            | EventName.AIOBOTOCORE
            | EventName.OPENAI
            | EventName.ANTHROPIC
        ):
            return True
        case _:
            return False
