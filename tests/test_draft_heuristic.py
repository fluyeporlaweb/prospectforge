from __future__ import annotations

from prospectforge.draft import DRAFT_MARKER, heuristic_draft
from prospectforge.models import Lead
from prospectforge.qualify import heuristic_qualification

ICP = "Founders at small software companies in Spain"


def test_draft_contains_lead_details_and_is_short(leads) -> None:
    lead = leads[0]
    qualification = heuristic_qualification(lead, "A CLI that qualifies B2B leads", ICP)
    draft = heuristic_draft(lead, qualification, "A CLI that qualifies B2B leads")
    assert "Alex" in draft.body
    assert "Northwind Software" in draft.body
    assert DRAFT_MARKER in draft.body
    assert len(draft.body.split()) <= 120
    assert len(draft.subject.split()) <= 8
    assert "{" not in draft.body and "}" not in draft.body
    assert draft.source == "heuristic"


def test_draft_handles_missing_name_and_company() -> None:
    lead = Lead(email="someone@example.com")
    qualification = heuristic_qualification(lead, "A CLI", "founders in Spain")
    draft = heuristic_draft(lead, qualification, "A CLI")
    assert "Hi there" in draft.body
    assert "{" not in draft.body and "}" not in draft.body
    assert len(draft.body.split()) <= 120
