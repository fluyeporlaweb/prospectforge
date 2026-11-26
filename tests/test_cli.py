from __future__ import annotations

import csv
import json
from pathlib import Path

from typer.testing import CliRunner

from prospectforge.cli import app
from prospectforge.export import LEAD_COLUMNS

runner = CliRunner()


def test_help_for_app_and_all_commands() -> None:
    for args in (
        ["--help"],
        ["discover", "--help"],
        ["qualify", "--help"],
        ["draft", "--help"],
        ["run", "--help"],
    ):
        result = runner.invoke(app, args)
        assert result.exit_code == 0, result.output


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_discover_dry_run_prints_input_without_apify(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APIFY_TOKEN", "fake-token-not-real")

    def boom(*args, **kwargs):
        raise AssertionError("Apify must not be called in dry-run mode")

    monkeypatch.setattr("prospectforge.apify_client.ApifyRunner.run_actor", boom)

    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app,
        ["discover", "--titles", "founder", "--countries", "es", "--max", "2", "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["jobTitles"] == ["founder"]
    assert payload["countries"] == ["es"]
    assert payload["maxResults"] == 2
    assert not (tmp_path / "out").exists()


def test_discover_max_is_not_clamped_upward() -> None:
    result = runner.invoke(
        app,
        ["discover", "--titles", "founder", "--max", "2", "--dry-run"],
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["maxResults"] == 2


def test_discover_rejects_out_of_range_max() -> None:
    result = runner.invoke(app, ["discover", "--max", "501", "--dry-run"])
    assert result.exit_code == 2
    assert "between" in result.output.lower()


def test_discover_live_without_token_exits_2_with_hint() -> None:
    result = runner.invoke(app, ["discover", "--titles", "founder", "--max", "2"])
    assert result.exit_code == 2
    assert "APIFY_TOKEN" in result.output
    assert "apify.com" in result.output.lower()


def test_discover_csv_uses_fixed_columns(monkeypatch, tmp_path: Path) -> None:
    raw = json.loads(
        (Path(__file__).parent / "fixtures" / "b2bsearch_raw.json").read_text(encoding="utf-8")
    )
    monkeypatch.setenv("APIFY_TOKEN", "fake-token-not-real")

    def fake_run(self, actor_id, run_input, *, max_results):
        return raw[:max_results]

    monkeypatch.setattr("prospectforge.apify_client.ApifyRunner.run_actor", fake_run)
    out = tmp_path / "leads.csv"
    result = runner.invoke(
        app,
        [
            "discover",
            "--titles",
            "founder",
            "--max",
            "2",
            "--format",
            "csv",
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    with out.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0].keys()) == LEAD_COLUMNS
    assert len(rows) == 2


def test_run_without_input_or_live_refuses(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["run", "--product", "p", "--icp", "i", "--dry-run", "--out", str(tmp_path)],
    )
    assert result.exit_code == 2
    assert "--live" in result.output
    assert "--input" in result.output


def test_run_with_input_dry_run_writes_outputs(leads, tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "run",
            "--product",
            "A CLI that qualifies B2B leads",
            "--icp",
            "Founders at small software companies in Spain",
            "--input",
            str(Path(__file__).parent / "fixtures" / "leads.json"),
            "--dry-run",
            "--out",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (out / "leads.json").exists()
    assert (out / "leads.csv").exists()
    assert (out / "drafts.json").exists()
    assert "Discovered 5 leads" in result.output


def test_qualify_and_draft_dry_run(leads, tmp_path: Path) -> None:
    qualifications = tmp_path / "qualifications.json"
    result = runner.invoke(
        app,
        [
            "qualify",
            "--input",
            str(Path(__file__).parent / "fixtures" / "leads.json"),
            "--product",
            "A CLI that qualifies B2B leads",
            "--icp",
            "Founders at small software companies in Spain",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["lead_key"] == leads[0].key
    assert not qualifications.exists()

    full = runner.invoke(
        app,
        [
            "qualify",
            "--input",
            str(Path(__file__).parent / "fixtures" / "leads.json"),
            "--product",
            "A CLI that qualifies B2B leads",
            "--icp",
            "Founders at small software companies in Spain",
            "--out",
            str(tmp_path),
        ],
    )
    assert full.exit_code == 0, full.output
    assert qualifications.exists()

    draft_result = runner.invoke(
        app,
        [
            "draft",
            "--input",
            str(Path(__file__).parent / "fixtures" / "leads.json"),
            "--qualifications",
            str(qualifications),
            "--product",
            "A CLI that qualifies B2B leads",
            "--dry-run",
        ],
    )
    assert draft_result.exit_code == 0, draft_result.output
    assert json.loads(draft_result.output)["lead_key"] == leads[0].key
