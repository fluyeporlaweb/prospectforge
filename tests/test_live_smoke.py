from __future__ import annotations

import os

import pytest

from prospectforge.config import SMOKE_MAX
from prospectforge.discover.b2bsearch import B2BSearchProvider

pytestmark = pytest.mark.apify


@pytest.mark.skipif(not os.environ.get("APIFY_TOKEN"), reason="APIFY_TOKEN not set")
def test_b2bsearch_live_smoke() -> None:
    provider = B2BSearchProvider()
    actor_input = {
        "jobTitles": ["founder"],
        "countries": ["es"],
        "maxResults": 2,
        "includePhones": False,
    }
    raw_items = provider.run(actor_input, max_results=2)
    assert len(raw_items) <= SMOKE_MAX
    for raw in raw_items:
        lead = provider.normalize(raw)
        assert lead.provider == "b2bsearch"
