from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..models import IcpFilters, Lead


def first_present(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return item[key]
    return None


def clean_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    return [value.strip() for value in values if value and value.strip()]


def build_base_input(filters: IcpFilters, max_results: int) -> dict[str, Any]:
    data: dict[str, Any] = {"maxResults": max_results}
    if filters.company_size_min is not None:
        data["companySizeMin"] = filters.company_size_min
    if filters.company_size_max is not None:
        data["companySizeMax"] = filters.company_size_max
    return data


@runtime_checkable
class LeadProvider(Protocol):
    name: str
    actor_id: str

    def build_input(
        self,
        filters: IcpFilters,
        max_results: int,
        *,
        email_type: str = "any",
    ) -> dict[str, Any]: ...

    def run(self, actor_input: dict[str, Any], *, max_results: int) -> list[dict[str, Any]]: ...

    def normalize(self, raw: dict[str, Any]) -> Lead: ...
