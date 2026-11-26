from __future__ import annotations

import pytest
from pydantic import ValidationError

from prospectforge.models import (
    Draft,
    Lead,
    Qualification,
    infer_email_type,
    normalize_domain,
    verdict_for_score,
)


def test_bad_email_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Lead(email="not-an-email")


def test_raw_source_passthrough() -> None:
    raw = {"id": "x", "unknownField": ["a", "b"]}
    lead = Lead(provider="b2bsearch", name="A Fake", raw_source=raw)
    assert lead.raw_source == raw
    assert lead.raw_source["unknownField"] == ["a", "b"]


def test_email_type_inference() -> None:
    assert infer_email_type("a@yahoo.com") == "personal"
    assert infer_email_type("a@example.com") == "work"
    assert infer_email_type(None) == "none"
    assert infer_email_type("a@gmail.com") == "personal"


def test_lead_key_is_stable_without_email() -> None:
    first = Lead(name="A Fake", company="Fake Co")
    second = Lead(name="A Fake", company="Fake Co")
    assert first.key == second.key
    assert first.key.startswith("lead:")
    with_email = Lead(name="A Fake", email="a@example.com")
    assert with_email.key == "a@example.com"


def test_verdict_bands() -> None:
    assert verdict_for_score(70) == "strong"
    assert verdict_for_score(69) == "ok"
    assert verdict_for_score(40) == "ok"
    assert verdict_for_score(39) == "weak"
    assert verdict_for_score(15) == "weak"
    assert verdict_for_score(14) == "bad"


def test_qualification_and_draft_validation() -> None:
    qualification = Qualification(
        lead_key="a@example.com", score=80, verdict="strong", source="heuristic"
    )
    assert qualification.reasons == []
    draft = Draft(lead_key="a@example.com", subject="Hi", body="Body", source="heuristic")
    assert draft.subject == "Hi"
    with pytest.raises(ValidationError):
        Qualification(lead_key="a@example.com", score=101, verdict="strong", source="heuristic")


def test_normalize_domain() -> None:
    assert normalize_domain("https://www.Example.com/path") == "example.com"
    assert normalize_domain("user@example.com") == "example.com"
    assert normalize_domain(None) is None
