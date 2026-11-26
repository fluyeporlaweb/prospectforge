from __future__ import annotations

from collections.abc import Callable

from ..errors import ConfigError
from .b2bsearch import B2BSearchProvider
from .base import LeadProvider
from .olympus import OlympusProvider

PROVIDERS: dict[str, Callable[[], LeadProvider]] = {
    "b2bsearch": B2BSearchProvider,
    "olympus": OlympusProvider,
}


def get_provider(name: str) -> LeadProvider:
    try:
        provider = PROVIDERS[name]
    except KeyError as exc:
        choices = ", ".join(sorted(PROVIDERS))
        raise ConfigError(f"Unknown provider {name!r}. Choose one of: {choices}.") from exc
    return provider()


__all__ = ["B2BSearchProvider", "LeadProvider", "OlympusProvider", "get_provider"]
