from __future__ import annotations

from typing import Any

from .config import (
    DEFAULT_MAX_RESULTS,
    DEFAULT_MIN_SCORE,
    DEFAULT_PROVIDER,
    get_openai_api_key,
    resolve_max_results,
    validate_min_score,
)
from .discover import get_provider
from .discover.base import LeadProvider
from .draft import build_drafter
from .llm import LLMClient, OpenAICompatClient
from .models import Draft, IcpFilters, Lead, PipelineResult, Qualification
from .qualify import build_qualifier


def make_llm_client(model: str | None, dry_run: bool) -> LLMClient | None:
    if dry_run or get_openai_api_key() is None:
        return None
    return OpenAICompatClient(model=model)


class Pipeline:
    def __init__(
        self,
        *,
        product: str,
        icp: str,
        provider: str = DEFAULT_PROVIDER,
        filters: IcpFilters | None = None,
        max_results: int = DEFAULT_MAX_RESULTS,
        min_score: int = DEFAULT_MIN_SCORE,
        model: str | None = None,
        dry_run: bool = True,
        email_type: str = "any",
        llm_client: LLMClient | None = None,
        provider_obj: LeadProvider | None = None,
    ) -> None:
        self.product = product
        self.icp = icp
        self.provider = provider
        self.filters = filters or IcpFilters()
        self.max_results = resolve_max_results(max_results)
        self.min_score = validate_min_score(min_score)
        self.model = model
        self.dry_run = dry_run
        self.email_type = email_type
        self._llm_client = llm_client
        self._provider_obj = provider_obj

    def _resolve_provider(self) -> LeadProvider:
        if self._provider_obj is not None:
            return self._provider_obj
        return get_provider(self.provider)

    def discover(self) -> list[Lead]:
        provider = self._resolve_provider()
        actor_input = provider.build_input(
            self.filters,
            self.max_results,
            email_type=self.email_type,
        )
        raw_items = provider.run(actor_input, max_results=self.max_results)
        return [provider.normalize(raw) for raw in raw_items[: self.max_results]]

    def run(self, leads: list[Lead] | None = None) -> PipelineResult:
        discovered = list(leads) if leads is not None else self.discover()

        client = self._llm_client
        if client is None:
            client = make_llm_client(self.model, self.dry_run)

        qualifier = build_qualifier(client, self.filters)
        drafter = build_drafter(client)

        qualifications: list[Qualification] = []
        drafts: list[Draft] = []
        for lead in discovered:
            qualification = qualifier.qualify(lead, self.product, self.icp)
            qualifications.append(qualification)
            if lead.email and qualification.score >= self.min_score:
                drafts.append(drafter.draft(lead, qualification, self.product))

        by_verdict: dict[str, int] = {"strong": 0, "ok": 0, "weak": 0, "bad": 0}
        for qualification in qualifications:
            by_verdict[qualification.verdict] += 1

        summary: dict[str, Any] = {
            "provider": self.provider,
            "discovered": len(discovered),
            "qualified": len(qualifications),
            "drafted": len(drafts),
            "min_score": self.min_score,
            "by_verdict": by_verdict,
            "llm_used": client is not None,
            "llm_qualifications": sum(1 for q in qualifications if q.source == "llm"),
            "dry_run": self.dry_run,
        }
        return PipelineResult(
            product=self.product,
            icp=self.icp,
            provider=self.provider,
            leads=discovered,
            qualifications=qualifications,
            drafts=drafts,
            summary=summary,
        )
