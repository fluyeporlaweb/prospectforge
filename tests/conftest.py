from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from prospectforge.models import Lead

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _clean_secret_env(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    if request.node.get_closest_marker("apify"):
        return
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("PROSPECTFORGE_MODEL", raising=False)


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


@pytest.fixture
def leads() -> list[Lead]:
    data: list[dict[str, Any]] = json.loads((FIXTURES / "leads.json").read_text(encoding="utf-8"))
    return [Lead.model_validate(item) for item in data]


@pytest.fixture
def sample_lead() -> Lead:
    return Lead(
        name="Sam Example",
        title="Founder",
        email="sam@example.com",
        company="Example Software",
        company_domain="example.com",
        industry="Software",
        country="es",
        company_size="11-50",
    )
