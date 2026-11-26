from __future__ import annotations

import json

from prospectforge.discover.b2bsearch import B2BSearchProvider
from prospectforge.models import IcpFilters


def test_build_input_full_filter_set() -> None:
    provider = B2BSearchProvider()
    filters = IcpFilters(
        titles=["founder", "ceo"],
        exclude_titles=["intern"],
        departments=["sales"],
        seniority=["founder"],
        countries=["es"],
        cities=["madrid"],
        industries=["software"],
        keywords=["saas"],
        company_domains=["example.com"],
        exclude_domains=["bad.example"],
        company_size_min=11,
        company_size_max=50,
    )
    actor_input = provider.build_input(filters, 2, email_type="work")
    assert actor_input == {
        "maxResults": 2,
        "emailType": "work",
        "includePhones": False,
        "includeSocialLinks": True,
        "jobTitles": ["founder", "ceo"],
        "excludeJobTitles": ["intern"],
        "departments": ["sales"],
        "seniority": ["founder"],
        "countries": ["es"],
        "cities": ["madrid"],
        "industries": ["software"],
        "keywords": ["saas"],
        "companyDomains": ["example.com"],
        "excludeCompanyDomains": ["bad.example"],
        "companySizeMin": 11,
        "companySizeMax": 50,
    }


def test_build_input_omits_empty_filters_and_sends_explicit_max() -> None:
    actor_input = B2BSearchProvider().build_input(IcpFilters(), 25)
    assert actor_input["maxResults"] == 25
    assert "jobTitles" not in actor_input
    assert "countries" not in actor_input
    assert actor_input["includePhones"] is False
    assert actor_input["includeSocialLinks"] is True


def test_normalize_fixture(fixtures_dir) -> None:
    raw_items = json.loads((fixtures_dir / "b2bsearch_raw.json").read_text(encoding="utf-8"))
    provider = B2BSearchProvider()

    first = provider.normalize(raw_items[0])
    assert first.name == "Ana Fake"
    assert first.title == "Founder"
    assert first.email == "ana.founder@example.com"
    assert first.email_type == "work"
    assert first.company == "FakeSoft SL"
    assert first.company_domain == "fakesoft.example"
    assert first.company_size == "11-50"
    assert first.country == "es"
    assert first.linkedin_url == "https://www.linkedin.com/in/fake-ana"
    assert first.raw_source["id"] == "b2b-fixture-1"
    assert first.raw_source["phoneOnRecord"] is True

    second = provider.normalize(raw_items[1])
    assert second.name == "Ben Fake"
    assert second.title == "CTO"
    assert second.email_type == "personal"
    assert second.company_domain == "fakeworks.example"
    assert second.company_size == "25"
    assert second.country == "us"
    assert second.seniority == "c_suite"

    third = provider.normalize(raw_items[2])
    assert third.email is None
    assert third.email_type == "none"
    assert third.company_domain == "fakeagency.example"
