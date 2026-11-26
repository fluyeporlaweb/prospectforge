from __future__ import annotations

import json

import pytest

from prospectforge.discover.olympus import OlympusProvider
from prospectforge.errors import ConfigError
from prospectforge.models import IcpFilters


def test_build_input_uses_arrays_and_full_country_names() -> None:
    provider = OlympusProvider()
    filters = IcpFilters(
        titles=["founder", "ceo"],
        exclude_titles=["intern"],
        departments=["Executive"],
        seniority=["founder", "CEO", "wizard"],
        countries=["es", "us"],
        industries=["Software", "SaaS"],
        keywords=["b2b"],
        company_domains=["one.example", "two.example"],
    )
    actor_input = provider.build_input(filters, 25)
    assert actor_input["maxResults"] == 25
    assert actor_input["personTitle"] == ["founder", "ceo"]
    assert actor_input["excludeTitle"] == ["intern"]
    assert actor_input["department"] == ["Executive"]
    assert actor_input["seniority"] == ["founder", "c_suite"]
    assert actor_input["personCountry"] == ["Spain", "United States"]
    assert actor_input["industry"] == ["Software", "SaaS"]
    assert actor_input["webKeywords"] == ["b2b"]
    assert actor_input["companyDomain"] == ["one.example", "two.example"]


def test_build_input_defaults_to_small_explicit_max() -> None:
    actor_input = OlympusProvider().build_input(IcpFilters(), 25)
    assert actor_input == {"maxResults": 25}


def test_build_input_rejects_too_many_domains() -> None:
    filters = IcpFilters(company_domains=[f"d{i}.example" for i in range(101)])
    with pytest.raises(ConfigError):
        OlympusProvider().build_input(filters, 25)


def test_normalize_fixture(fixtures_dir) -> None:
    raw_items = json.loads((fixtures_dir / "olympus_raw.json").read_text(encoding="utf-8"))
    provider = OlympusProvider()

    first = provider.normalize(raw_items[0])
    assert first.name == "Ola Fake"
    assert first.title == "Founder"
    assert first.email == "ola.founder@example.com"
    assert first.department == "Executive"
    assert first.seniority == "founder"
    assert first.country == "es"
    assert first.company == "Fake Olympus SL"
    assert first.company_domain == "fakeolympus.example"
    assert first.company_size == "11 - 50"
    assert first.raw_source["id"] == "oly-fixture-1"

    second = provider.normalize(raw_items[1])
    assert second.name == "Pablo Fake"
    assert second.email is None
    assert second.email_type == "none"
    assert second.country == "es"
    assert second.company_domain == "fakeolympuslabs.example"

    third = provider.normalize(raw_items[2])
    assert third.name == "Quinn Fake"
    assert third.email_type == "personal"
    assert third.country == "us"
    assert third.company == "Fake US Sales Co"
