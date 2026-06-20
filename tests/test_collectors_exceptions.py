from pai.collectors import exceptions


def raise_key_error() -> str:
    payload = {"name": "John"}
    return payload["user_id"]


def test_build_exception_event_from_traceback() -> None:
    try:
        raise_key_error()
    except KeyError as error:
        tb = error.__traceback__
        assert tb is not None
        event = exceptions.build_exception_event(type(error), error, tb)

    assert event.exception_type == "KeyError"
    assert event.message == "'user_id'"
    assert event.symbol.endswith(".raise_key_error")
    assert event.file.endswith(".py")
    assert isinstance(event.line, int)
    assert event.locals_schema["payload"] == {"type": "dict", "keys": ["name"]}
