from __future__ import annotations

import csv
import json
from pathlib import Path

from prospectforge.export import export_result
from prospectforge.pipeline import Pipeline
from prospectforge.qualify import heuristic_qualification


def test_pipeline_with_input_fixture_is_fully_offline(leads, tmp_path: Path) -> None:
    pipeline = Pipeline(
        product="A CLI that qualifies B2B leads",
        icp="Founders at small software companies in Spain",
        dry_run=True,
        min_score=60,
    )
    result = pipeline.run(leads)

    assert len(result.leads) == 5
    assert len(result.qualifications) == 5
    assert len(result.drafts) == 2
    assert result.summary["discovered"] == 5
    assert result.summary["qualified"] == 5
    assert result.summary["drafted"] == 2
    assert result.summary["by_verdict"] == {"strong": 2, "ok": 1, "weak": 1, "bad": 1}
    assert result.summary["llm_used"] is False
    assert result.summary["dry_run"] is True

    drafted_keys = {draft.lead_key for draft in result.drafts}
    assert drafted_keys == {leads[0].key, leads[1].key}
    assert all("@" in draft.lead_key for draft in result.drafts)

    export_result(tmp_path, result)
    for name in ("leads.json", "leads.csv", "drafts.json", "drafts.csv"):
        assert (tmp_path / name).exists()

    full = json.loads((tmp_path / "leads.json").read_text(encoding="utf-8"))
    assert full["product"] == "A CLI that qualifies B2B leads"
    assert len(full["leads"]) == 5
    assert len(full["drafts"]) == 2

    with (tmp_path / "leads.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 5
    assert rows[0]["lead_key"] == leads[0].key
    assert rows[0]["score"] == "85"


def test_pipeline_skips_drafting_leads_without_email(leads) -> None:
    pipeline = Pipeline(
        product="A CLI",
        icp="Founders at small software companies in Spain",
        dry_run=True,
        min_score=0,
    )
    result = pipeline.run(leads)
    drafted_keys = {draft.lead_key for draft in result.drafts}
    assert leads[4].key not in drafted_keys


def test_pipeline_is_deterministic(leads) -> None:
    first = heuristic_qualification(leads[0], "p", "Founders at software companies in Spain")
    second = heuristic_qualification(leads[0], "p", "Founders at software companies in Spain")
    assert first.model_dump() == second.model_dump()
