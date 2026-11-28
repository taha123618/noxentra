"""Plugin & Tool Adapter SDK for extending Noxentra without modifying core."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from typing import Protocol

from noxentra.findings import Finding

SDK_VERSION = "1.0"


@dataclass(frozen=True)
class PluginMetadata:
    """Declarative metadata and trust/compatibility declaration for an external adapter."""

    name: str
    version: str
    sdk_version: str
    binary: str
    risk_level: str = "moderate"
    tags: tuple[str, ...] = ()
    description: str = ""


class PluginAdapter(Protocol):
    """Standard interface for third-party tool adapters."""

    metadata: PluginMetadata

    def build_argv(self, target: str, options: dict | None = None) -> list[str]:
        ...

    def parse_output(self, raw: str, timestamp: str) -> list[Finding]:
        ...


@dataclass
class PluginRegistry:
    """In-memory registry enforcing SDK version compatibility and trust checks."""

    adapters: dict[str, PluginAdapter] = field(default_factory=dict)

    def register(self, adapter: PluginAdapter) -> None:
        meta = adapter.metadata
        if meta.sdk_version.split(".")[0] != SDK_VERSION.split(".")[0]:
            raise ValueError(
                f"Incompatible plugin SDK version {meta.sdk_version!r} for {meta.name!r} (expected {SDK_VERSION})"
            )
        if meta.risk_level not in ("low", "moderate", "high", "restricted"):
            raise ValueError(f"Invalid risk_level {meta.risk_level!r} for plugin {meta.name!r}")
        self.adapters[meta.name] = adapter

    def is_installed(self, name: str) -> bool:
        adapter = self.adapters.get(name)
        if adapter is None:
            return False
        return shutil.which(adapter.metadata.binary) is not None
