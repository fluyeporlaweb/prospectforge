from __future__ import annotations

from typing import Any

from ..apify_client import ApifyRunner
from ..config import B2BSEARCH_ACTOR_ID
from ..models import IcpFilters, Lead, infer_email_type, normalize_domain
from .base import clean_list, first_present


class B2BSearchProvider:
    name = "b2bsearch"
    actor_id = B2BSEARCH_ACTOR_ID

    def __init__(self, runner: ApifyRunner | None = None) -> None:
        self._runner = runner

    def build_input(
        self,
        filters: IcpFilters,
        max_results: int,
        *,
        email_type: str = "any",
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "maxResults": max_results,
            "emailType": email_type if email_type in {"any", "work", "personal"} else "any",
            "includePhones": False,
            "includeSocialLinks": True,
        }
        list_map = {
            "jobTitles": filters.titles,
            "excludeJobTitles": filters.exclude_titles,
            "departments": filters.departments,
            "seniority": filters.seniority,
            "countries": filters.countries,
            "cities": filters.cities,
            "industries": filters.industries,
            "keywords": filters.keywords,
            "companyDomains": filters.company_domains,
            "excludeCompanyDomains": filters.exclude_domains,
        }
        for actor_key, values in list_map.items():
            cleaned = clean_list(values)
            if cleaned:
                data[actor_key] = cleaned
        if filters.company_size_min is not None:
            data["companySizeMin"] = filters.company_size_min
        if filters.company_size_max is not None:
            data["companySizeMax"] = filters.company_size_max
        return data

    def run(self, actor_input: dict[str, Any], *, max_results: int) -> list[dict[str, Any]]:
        runner = self._runner or ApifyRunner()
        items = runner.run_actor(self.actor_id, actor_input, max_results=max_results)
        return items[:max_results]

    def normalize(self, raw: dict[str, Any]) -> Lead:
        email = first_present(raw, "email", "emailAddress")
        company_size = first_present(raw, "companySize", "employees", "employeeCount")
        domain = first_present(raw, "companyDomain", "website", "domain")
        return Lead(
            provider="b2bsearch",
            name=first_present(raw, "name", "fullName", "full_name"),
            title=first_present(raw, "title", "jobTitle", "job_title"),
            department=first_present(raw, "department", "function"),
            seniority=first_present(raw, "seniority", "seniorityLevel"),
            email=email,
            email_type=infer_email_type(email),
            phone=first_present(raw, "phone", "phoneNumber", "mobile"),
            company=first_present(raw, "company", "companyName", "organization"),
            company_domain=normalize_domain(domain if isinstance(domain, str) else None),
            company_size=str(company_size) if company_size is not None else None,
            industry=first_present(raw, "industry", "companyIndustry"),
            country=first_present(raw, "country", "countryCode", "country_code"),
            city=first_present(raw, "city", "location"),
            linkedin_url=first_present(raw, "linkedinUrl", "linkedin", "linkedin_url"),
            raw_source=raw,
        )
