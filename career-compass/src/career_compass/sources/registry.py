"""Adapter name → implementation.

The only place adapter names are bound to code. `config/sources.yaml` names an
adapter; this maps it. An unknown name is a ConfigError at load time.
"""

from __future__ import annotations

from career_compass.sources.base import SourceAdapter

_REGISTRY: dict[str, type[SourceAdapter]] = {}


def register(name: str):
    """Decorator. Adapters self-register on import."""
    raise NotImplementedError


def get_adapter(name: str) -> SourceAdapter:
    """Resolve an adapter by config name, e.g. "ats.greenhouse"."""
    raise NotImplementedError


def known_adapters() -> list[str]:
    raise NotImplementedError
