from __future__ import annotations

import re
from typing import Any

from .errors import LLMParseError, ProviderError
from .icp import ISO2_TO_NAME, extract_keywords, normalize_country_code
from .llm import LLMClient
from .models import IcpFilters, Lead, Qualification, email_domain, verdict_for_score

SENIORITY_RULES: list[tuple[tuple[str, ...], int, str]] = [
    (("founder", "co-founder", "cofounder", "owner"), 25, "founder/owner"),
    (("ceo", "cto", "cfo", "coo", "cmo", "chief", "c-level", "c_suite"), 25, "c-level"),
    (("partner",), 20, "partner"),
    (("vp", "vice president", "head of", "head"), 15, "vp/head"),
    (("director",), 15, "director"),
    (("manager",), 8, "manager"),
    (("senior", "lead"), 5, "senior"),
]


def _lead_text(lead: Lead) -> str:
    parts = [
        lead.name,
        lead.title,
        lead.department,
        lead.seniority,
        lead.company,
        lead.industry,
        lead.country,
        lead.city,
        lead.company_size,
        lead.company_domain,
    ]
    if lead.country:
        try:
            parts.append(ISO2_TO_NAME.get(normalize_country_code(lead.country)))
        except Exception:  # noqa: BLE001 - country is only extra context
            pass
    return " ".join(part for part in parts if part).lower()


def _seniority_signal(lead: Lead) -> tuple[int, str | None]:
    haystack = f"{lead.title or ''} {lead.seniority or ''}".lower()
    for keywords, boost, label in SENIORITY_RULES:
        if any(keyword in haystack for keyword in keywords):
            return boost, label
    return 0, None


def heuristic_qualification(
    lead: Lead,
    product: str,
    icp: str,
    filters: IcpFilters | None = None,
) -> Qualification:
    filters = filters or IcpFilters()
    haystack = _lead_text(lead)

    exclude_domains = {domain.lower() for domain in filters.exclude_domains}
    lead_domains = {
        value
        for value in (lead.company_domain, email_domain(str(lead.email) if lead.email else None))
        if value
    }
    if exclude_domains and lead_domains & exclude_domains:
        return Qualification(
            lead_key=lead.key,
            score=0,
            verdict="bad",
            reasons=["Company domain is on the exclusion list."],
            source="heuristic",
        )

    icp_terms = extract_keywords(icp)
    for extra in [*filters.keywords, *filters.industries, *filters.titles]:
        for token in extract_keywords(extra):
            if token not in icp_terms:
                icp_terms.append(token)

    matched = [term for term in icp_terms if re.search(rf"\b{re.escape(term)}\b", haystack)]
    score = min(100, len(matched) * 20)
    reasons: list[str] = []

    if matched:
        reasons.append("Matched ICP keywords: " + ", ".join(matched[:5]) + ".")
    else:
        reasons.append("No ICP keywords matched the lead profile.")

    boost, label = _seniority_signal(lead)
    if boost:
        score = min(100, score + boost)
        reasons.append(f"Seniority signal: {label} (+{boost}).")

    if filters.countries and lead.country:
        try:
            lead_code = normalize_country_code(lead.country)
        except Exception:  # noqa: BLE001 - unmatched country is not fatal
            lead_code = None
        if lead_code and lead_code in {normalize_country_code(c) for c in filters.countries}:
            score = min(100, score + 10)
            reasons.append(f"Located in target country ({lead_code}).")

    title = (lead.title or "").lower()
    excluded_titles = [value for value in filters.exclude_titles if value.lower() in title]
    if excluded_titles:
        score = max(0, score - 50)
        reasons.append("Title is on the exclusion list: " + ", ".join(excluded_titles) + ".")

    if not lead.email:
        reasons.append("No email on record; excluded from drafting.")

    verdict = verdict_for_score(score)
    return Qualification(
        lead_key=lead.key,
        score=score,
        verdict=verdict,
        reasons=reasons[:4],
        source="heuristic",
    )


class HeuristicQualifier:
    def __init__(self, filters: IcpFilters | None = None) -> None:
        self._filters = filters

    def qualify(self, lead: Lead, product: str, icp: str) -> Qualification:
        return heuristic_qualification(lead, product, icp, self._filters)


class LLMQualifier:
    def __init__(self, client: LLMClient, filters: IcpFilters | None = None) -> None:
        self._client = client
        self._filters = filters

    def qualify(self, lead: Lead, product: str, icp: str) -> Qualification:
        try:
            return self._client.qualify(lead, product, icp)
        except (LLMParseError, ProviderError):
            return heuristic_qualification(lead, product, icp, self._filters)


def build_qualifier(
    client: LLMClient | None,
    filters: IcpFilters | None = None,
) -> HeuristicQualifier | LLMQualifier:
    if client is None:
        return HeuristicQualifier(filters)
    return LLMQualifier(client, filters)


def qualification_payload(qualification: Qualification) -> dict[str, Any]:
    return qualification.model_dump()
