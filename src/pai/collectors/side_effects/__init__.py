"""Side-effect collectors — HTTP, SQL, AWS, AI, and more.

Each integration is declared as a ``SideEffectIntegration`` entry. When the named
module is first imported in the target process, the ``patch`` callback fires once
with the live module and a shared ``writer``.

To add a new integration, append an entry to ``make_integrations`` — no other wiring needed.
"""

import contextlib
import types
from collections.abc import Callable
from dataclasses import dataclass

from pai.collectors.imports import ImportCollector
from pai.collectors.side_effects import ai, aws, http, sql
from pai.writer import EventWriter

__all__ = ["SideEffectIntegration", "install", "make_integrations"]


@dataclass
class SideEffectIntegration:
    """Maps an import trigger to a patching callback."""

    module: str
    patch: Callable[[types.ModuleType], None]


def make_integrations(writer: EventWriter) -> list[SideEffectIntegration]:
    """Build all registered side-effect integrations for a given writer."""
    http_collector = http.HttpCollector(writer=writer)
    sql_collector = sql.SqlCollector(writer=writer)
    aws_collector = aws.AwsCollector(writer=writer)
    ai_collector = ai.AiCollector(writer=writer)

    def on_requests(mod: types.ModuleType) -> None:
        http.patch_requests(http_collector, mod, mod.Session)

    def on_httpx(mod: types.ModuleType) -> None:
        http.patch_httpx(http_collector, mod)

    def on_sqlalchemy(mod: types.ModuleType) -> None:
        with contextlib.suppress(AttributeError):
            sql.patch_sqlalchemy(sql_collector, mod.engine.Connection)

    def on_asyncpg(mod: types.ModuleType) -> None:
        with contextlib.suppress(AttributeError):
            sql.patch_asyncpg(sql_collector, mod.connection.Connection)

    def on_botocore(mod: types.ModuleType) -> None:
        with contextlib.suppress(AttributeError):
            aws.patch_botocore(aws_collector, mod.client.BaseClient)

    def on_aiobotocore(mod: types.ModuleType) -> None:
        with contextlib.suppress(AttributeError):
            aws.patch_aiobotocore(aws_collector, mod.client.AioBaseClient)

    def on_openai(mod: types.ModuleType) -> None:
        try:
            completions = mod.resources.chat.completions
        except AttributeError:
            return
        with contextlib.suppress(AttributeError):
            ai.patch_openai(ai_collector, completions.Completions)
        with contextlib.suppress(AttributeError):
            ai.patch_openai_async(ai_collector, completions.AsyncCompletions)

    def on_anthropic(mod: types.ModuleType) -> None:
        try:
            messages = mod.resources.messages
        except AttributeError:
            return
        with contextlib.suppress(AttributeError):
            ai.patch_anthropic(ai_collector, messages.Messages)
        with contextlib.suppress(AttributeError):
            ai.patch_anthropic_async(ai_collector, messages.AsyncMessages)

    return [
        SideEffectIntegration("requests", on_requests),
        SideEffectIntegration("httpx", on_httpx),
        SideEffectIntegration("sqlalchemy", on_sqlalchemy),
        SideEffectIntegration("asyncpg", on_asyncpg),
        SideEffectIntegration("botocore", on_botocore),
        SideEffectIntegration("aiobotocore", on_aiobotocore),
        SideEffectIntegration("openai", on_openai),
        SideEffectIntegration("anthropic", on_anthropic),
    ]


def install(writer: EventWriter, import_collector: ImportCollector) -> None:
    """Register all integration hooks with the import collector."""
    for integration in make_integrations(writer):
        import_collector.register_hook(integration.module, integration.patch)
