"""Transport selection / registry (spec: Transport Manager).

Phase 1: explicit registry (tests register fakes; the app registers the
USB transport in Phase 3). Discovery of physical USB devices arrives with the
USB transport.
"""
from __future__ import annotations

from typing import Callable

from ..errors import USBError
from .transport import Transport


class TransportRegistry:
    """Maps transport kind → factory."""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[..., Transport]] = {}

    def register(self, kind: str, factory: Callable[..., Transport]) -> None:
        if kind in self._factories:
            raise USBError(f"transport kind '{kind}' already registered", code="TRANSPORT_DUP")
        self._factories[kind] = factory

    def kinds(self) -> list[str]:
        return sorted(self._factories)

    def create(self, kind: str, **options: object) -> Transport:
        try:
            factory = self._factories[kind]
        except KeyError:
            raise USBError(
                f"unknown transport kind '{kind}'", code="TRANSPORT_UNKNOWN"
            ) from None
        return factory(**options)


class TransportManager:
    """Facade for opening/closing transports by kind."""

    def __init__(self, registry: TransportRegistry | None = None) -> None:
        self.registry = registry or TransportRegistry()

    def available(self) -> list[str]:
        return self.registry.kinds()

    def open(self, kind: str, options: dict | None = None) -> Transport:
        transport = self.registry.create(kind, **(options or {}))
        transport.open(options)
        return transport

    def close(self, transport: Transport) -> None:
        transport.close()
