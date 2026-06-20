"""Structured runtime events emitted by PAI collectors.

Events are stdlib-only dataclasses with an ``event`` string tag and a ``to_dict``
serializer. Known-shape nested dicts are described with ``TypedDict``.
"""

import dataclasses
from dataclasses import dataclass
from typing import ClassVar, NotRequired, TypedDict

from pai.event_names import EventName

__all__ = [
    "AiobotocoreEvent",
    "AnthropicEvent",
    "AsyncpgEvent",
    "Boto3Event",
    "CallEvent",
    "Event",
    "ExceptionEvent",
    "HttpxEvent",
    "ImportEvent",
    "LocalSchema",
    "OpenaiEvent",
    "RequestsEvent",
    "RunEndEvent",
    "RunStartEvent",
    "SqlalchemyEvent",
    "TestEvent",
]


class LocalSchema(TypedDict):
    """Schema of a single local variable — type name, and dict keys when applicable.

    Holds no raw values, only shape, to avoid leaking user data into events.
    """

    type: str
    keys: NotRequired[list[str]]


@dataclass
class Event:
    """Base for all events. Subclasses set ``event_name`` and declare fields.

    ``schema_version`` is included in every serialized event so consumers can adapt
    to future schema changes without breaking. ``timestamp`` is injected by
    ``EventWriter`` at write time rather than stored on the dataclass, keeping
    constructors free of generated defaults.
    """

    event_name: ClassVar[EventName]
    schema_version: ClassVar[int] = 1

    def to_dict(self) -> dict:
        data = dataclasses.asdict(self)

        result: dict = {
            "event": self.event_name,
            "schema_version": self.schema_version,
        }
        result.update(data)
        return result


@dataclass
class ExceptionEvent(Event):
    """An uncaught exception, located at the deepest frame of its traceback."""

    event_name: ClassVar[EventName] = EventName.EXCEPTION

    symbol: str
    file: str
    line: int
    exception_type: str
    message: str
    locals_schema: dict[str, LocalSchema]


@dataclass
class ImportEvent(Event):
    """A single import edge: ``module`` imported ``imported`` at runtime."""

    event_name: ClassVar[EventName] = EventName.IMPORT

    module: str
    imported: str


@dataclass
class RequestsEvent(Event):
    """An outbound HTTP request captured from requests."""

    event_name: ClassVar[EventName] = EventName.REQUESTS

    method: str
    url: str
    status_code: int
    duration_ms: int


@dataclass
class HttpxEvent(Event):
    """An outbound HTTP request captured from httpx."""

    event_name: ClassVar[EventName] = EventName.HTTPX

    method: str
    url: str
    status_code: int
    duration_ms: int


@dataclass
class SqlalchemyEvent(Event):
    """A SQL statement executed via SQLAlchemy."""

    event_name: ClassVar[EventName] = EventName.SQLALCHEMY

    operation: str
    query: str
    duration_ms: int


@dataclass
class AsyncpgEvent(Event):
    """A SQL statement executed via asyncpg."""

    event_name: ClassVar[EventName] = EventName.ASYNCPG

    operation: str
    query: str
    duration_ms: int


@dataclass
class Boto3Event(Event):
    """An AWS API call captured from botocore clients used by boto3."""

    event_name: ClassVar[EventName] = EventName.BOTO3

    service: str
    operation: str
    duration_ms: int


@dataclass
class AiobotocoreEvent(Event):
    """An AWS API call captured from aiobotocore clients."""

    event_name: ClassVar[EventName] = EventName.AIOBOTOCORE

    service: str
    operation: str
    duration_ms: int


@dataclass
class OpenaiEvent(Event):
    """An LLM completion call captured from the openai SDK."""

    event_name: ClassVar[EventName] = EventName.OPENAI

    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: int


@dataclass
class AnthropicEvent(Event):
    """An LLM completion call captured from the anthropic SDK."""

    event_name: ClassVar[EventName] = EventName.ANTHROPIC

    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: int


@dataclass
class CallEvent(Event):
    """A single Python function call with timing."""

    event_name: ClassVar[EventName] = EventName.CALL

    caller: str
    callee: str
    file: str
    line: int
    duration_ms: int


@dataclass
class TestEvent(Event):
    """Outcome of a single pytest test item."""

    event_name: ClassVar[EventName] = EventName.TEST

    test_id: str
    outcome: str
    duration_ms: int
    file: str
    message: str


@dataclass
class RunStartEvent(Event):
    """Emitted by the bootstrap as soon as the instrumented process starts."""

    event_name: ClassVar[EventName] = EventName.RUN_START

    command: list[str]
    cwd: str
    python_version: str


@dataclass
class RunEndEvent(Event):
    """Emitted by the runner after the instrumented subprocess exits."""

    event_name: ClassVar[EventName] = EventName.RUN_END

    exit_code: int
    duration_ms: int
