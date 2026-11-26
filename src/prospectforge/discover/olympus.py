from __future__ import annotations

from typing import Any

from ..apify_client import ApifyRunner
from ..config import OLYMPUS_ACTOR_ID
from ..errors import ConfigError
from ..icp import country_name, normalize_country_code, to_olympus_seniority
from ..models import IcpFilters, Lead, infer_email_type, normalize_domain
from .base import clean_list, first_present

MAX_DOMAINS = 100


class OlympusProvider:
    name = "olympus"
    actor_id = OLYMPUS_ACTOR_ID

    def __init__(self, runner: ApifyRunner | None = None) -> None:
        self._runner = runner

    def build_input(
        self,
        filters: IcpFilters,
        max_results: int,
        *,
        email_type: str = "any",
    ) -> dict[str, Any]:
        data: dict[str, Any] = {"maxResults": max_results}

        titles = clean_list(filters.titles)
        if titles:
            data["personTitle"] = titles
        exclude_titles = clean_list(filters.exclude_titles)
        if exclude_titles:
            data["excludeTitle"] = exclude_titles
        departments = clean_list(filters.departments)
        if departments:
            data["department"] = departments
        seniority = to_olympus_seniority(filters.seniority)
        if seniority:
            data["seniority"] = seniority
        countries = clean_list(filters.countries)
        if countries:
            data["personCountry"] = [country_name(code) for code in countries]
        industries = clean_list(filters.industries)
        if industries:
            data["industry"] = industries
        keywords = clean_list(filters.keywords)
        if keywords:
            data["webKeywords"] = keywords
        domains = clean_list(filters.company_domains)
        if len(domains) > MAX_DOMAINS:
            raise ConfigError(
                f"olympus accepts at most {MAX_DOMAINS} company domains; got {len(domains)}."
            )
        if domains:
            data["companyDomain"] = domains
        return data

    def run(self, actor_input: dict[str, Any], *, max_results: int) -> list[dict[str, Any]]:
        runner = self._runner or ApifyRunner()
        items = runner.run_actor(self.actor_id, actor_input, max_results=max_results)
        return items[:max_results]

    def normalize(self, raw: dict[str, Any]) -> Lead:
        email = first_present(raw, "email", "emailAddress")
        country_raw = first_present(raw, "personCountry", "country", "countryName")
        country: str | None = None
        if isinstance(country_raw, str) and country_raw:
            try:
                country = normalize_country_code(country_raw)
            except ConfigError:
                country = country_raw
        company_size = first_present(
            raw, "companyEmployeeSize", "companySize", "employees", "employeeCount"
        )
        domain = first_present(raw, "companyDomain", "websiteDomain", "website")
        return Lead(
            provider="olympus",
            name=first_present(raw, "name", "fullName", "full_name"),
            title=first_present(raw, "personTitle", "title", "jobTitle"),
            department=first_present(raw, "department", "function"),
            seniority=first_present(raw, "seniority", "seniorityLevel"),
            email=email,
            email_type=infer_email_type(email),
            phone=first_present(raw, "phone", "phoneNumber", "mobile"),
            company=first_present(raw, "companyName", "company", "organization"),
            company_domain=normalize_domain(domain if isinstance(domain, str) else None),
            company_size=str(company_size) if company_size is not None else None,
            industry=first_present(raw, "industry", "companyIndustry"),
            country=country,
            city=first_present(raw, "personCity", "city", "location"),
            linkedin_url=first_present(raw, "linkedinUrl", "linkedin", "linkedin_url"),
            raw_source=raw,
        )
