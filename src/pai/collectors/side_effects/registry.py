"""Registry for supported concrete side-effect package integrations."""

import contextlib
import types
from collections.abc import Callable
from dataclasses import dataclass

from pai.collectors.imports import ImportCollector
from pai.collectors.side_effects import (
    aiobotocore,
    anthropic,
    asyncpg,
    boto3,
    httpx,
    openai,
    requests,
    sqlalchemy,
)
from pai.writer import EventWriter

__all__ = ["SideEffectIntegration", "SideEffectRegistry", "install", "make_integrations"]


@dataclass
class SideEffectIntegration:
    """Maps an import trigger to a patching callback."""

    module: str
    patch: Callable[[types.ModuleType], None]


@dataclass
class SideEffectRegistry:
    """Owns concrete package collectors for one target process."""

    writer: EventWriter

    def integrations(self) -> list[SideEffectIntegration]:
        return [
            SideEffectIntegration("requests", self.patch_requests),
            SideEffectIntegration("httpx", self.patch_httpx),
            SideEffectIntegration("sqlalchemy", self.patch_sqlalchemy),
            SideEffectIntegration("asyncpg", self.patch_asyncpg),
            SideEffectIntegration("botocore", self.patch_boto3),
            SideEffectIntegration("aiobotocore", self.patch_aiobotocore),
            SideEffectIntegration("openai", self.patch_openai),
            SideEffectIntegration("anthropic", self.patch_anthropic),
        ]

    def patch_requests(self, mod: types.ModuleType) -> None:
        collector = requests.RequestsCollector(writer=self.writer)
        requests.patch_requests(collector, mod, mod.Session)

    def patch_httpx(self, mod: types.ModuleType) -> None:
        collector = httpx.HttpxCollector(writer=self.writer)
        httpx.patch_httpx(collector, mod)

    def patch_sqlalchemy(self, mod: types.ModuleType) -> None:
        collector = sqlalchemy.SqlalchemyCollector(writer=self.writer)
        with contextlib.suppress(AttributeError):
            sqlalchemy.patch_sqlalchemy(collector, mod.engine.Connection)

    def patch_asyncpg(self, mod: types.ModuleType) -> None:
        collector = asyncpg.AsyncpgCollector(writer=self.writer)
        with contextlib.suppress(AttributeError):
            asyncpg.patch_asyncpg(collector, mod.connection.Connection)

    def patch_boto3(self, mod: types.ModuleType) -> None:
        collector = boto3.Boto3Collector(writer=self.writer)
        with contextlib.suppress(AttributeError):
            boto3.patch_botocore(collector, mod.client.BaseClient)

    def patch_aiobotocore(self, mod: types.ModuleType) -> None:
        collector = aiobotocore.AiobotocoreCollector(writer=self.writer)
        with contextlib.suppress(AttributeError):
            aiobotocore.patch_aiobotocore(collector, mod.client.AioBaseClient)

    def patch_openai(self, mod: types.ModuleType) -> None:
        collector = openai.OpenaiCollector(writer=self.writer)
        try:
            completions = mod.resources.chat.completions
        except AttributeError:
            return

        with contextlib.suppress(AttributeError):
            openai.patch_openai(collector, completions.Completions)

        with contextlib.suppress(AttributeError):
            openai.patch_openai_async(collector, completions.AsyncCompletions)

    def patch_anthropic(self, mod: types.ModuleType) -> None:
        collector = anthropic.AnthropicCollector(writer=self.writer)
        try:
            messages = mod.resources.messages
        except AttributeError:
            return

        with contextlib.suppress(AttributeError):
            anthropic.patch_anthropic(collector, messages.Messages)

        with contextlib.suppress(AttributeError):
            anthropic.patch_anthropic_async(collector, messages.AsyncMessages)


def make_integrations(writer: EventWriter) -> list[SideEffectIntegration]:
    """Build all registered side-effect integrations for a given writer."""
    registry = SideEffectRegistry(writer=writer)
    return registry.integrations()


def install(writer: EventWriter, import_collector: ImportCollector) -> None:
    """Register all integration hooks with the import collector."""
    for integration in make_integrations(writer):
        import_collector.register_hook(integration.module, integration.patch)
