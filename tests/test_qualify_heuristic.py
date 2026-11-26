from __future__ import annotations

from prospectforge.models import IcpFilters
from prospectforge.qualify import heuristic_qualification

ICP = "Founders at small software companies in Spain"


def test_founder_scores_strong(leads) -> None:
    qualification = heuristic_qualification(leads[0], "A CLI that qualifies B2B leads", ICP)
    assert qualification.score == 85
    assert qualification.verdict == "strong"
    assert qualification.source == "heuristic"
    assert any("founder" in reason.lower() for reason in qualification.reasons)


def test_engineer_scores_ok(leads) -> None:
    qualification = heuristic_qualification(leads[2], "A CLI that qualifies B2B leads", ICP)
    assert qualification.score == 45
    assert qualification.verdict == "ok"


def test_non_icp_manager_scores_bad(leads) -> None:
    qualification = heuristic_qualification(leads[3], "A CLI that qualifies B2B leads", ICP)
    assert qualification.score == 8
    assert qualification.verdict == "bad"
    assert qualification.reasons


def test_excluded_domain_is_hard_zero(leads) -> None:
    filters = IcpFilters(exclude_domains=["northwind.example"])
    qualification = heuristic_qualification(
        leads[0], "A CLI that qualifies B2B leads", ICP, filters=filters
    )
    assert qualification.score == 0
    assert qualification.verdict == "bad"
    assert qualification.reasons == ["Company domain is on the exclusion list."]


def test_country_filter_adds_signal(leads) -> None:
    filters = IcpFilters(countries=["es"])
    qualification = heuristic_qualification(
        leads[2], "A CLI that qualifies B2B leads", ICP, filters=filters
    )
    assert qualification.score == 55
