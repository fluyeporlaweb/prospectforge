from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .errors import ConfigError
from .models import Draft, Lead, PipelineResult, Qualification

LEAD_COLUMNS = [
    "provider",
    "name",
    "title",
    "department",
    "seniority",
    "email",
    "email_type",
    "phone",
    "company",
    "company_domain",
    "company_size",
    "industry",
    "country",
    "city",
    "linkedin_url",
    "lead_key",
    "score",
    "verdict",
    "reasons",
]

DRAFT_COLUMNS = ["lead_key", "subject", "body", "source"]


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    )
    try:
        with handle:
            handle.write(text)
        os.replace(handle.name, path)
    except Exception:
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise


def write_json(path: Path, data: Any) -> None:
    _atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def to_leads_json(path: Path, leads: list[Lead]) -> None:
    write_json(path, [lead.model_dump(mode="json") for lead in leads])


def to_leads_csv(
    path: Path,
    leads: list[Lead],
    qualifications: list[Qualification] | None = None,
) -> None:
    by_key = {qualification.lead_key: qualification for qualification in qualifications or []}
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    )
    try:
        with handle:
            writer = csv.DictWriter(handle, fieldnames=LEAD_COLUMNS)
            writer.writeheader()
            for lead in leads:
                qualification = by_key.get(lead.key)
                row = lead.model_dump(mode="json")
                row["lead_key"] = lead.key
                row["score"] = qualification.score if qualification else ""
                row["verdict"] = qualification.verdict if qualification else ""
                row["reasons"] = " | ".join(qualification.reasons) if qualification else ""
                writer.writerow({column: row.get(column, "") for column in LEAD_COLUMNS})
        os.replace(handle.name, path)
    except Exception:
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise


def to_drafts_json(path: Path, drafts: list[Draft]) -> None:
    write_json(path, [draft.model_dump(mode="json") for draft in drafts])


def to_drafts_csv(path: Path, drafts: list[Draft]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    )
    try:
        with handle:
            writer = csv.DictWriter(handle, fieldnames=DRAFT_COLUMNS)
            writer.writeheader()
            for draft in drafts:
                writer.writerow(draft.model_dump(mode="json"))
        os.replace(handle.name, path)
    except Exception:
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise


def export_result(out_dir: Path, result: PipelineResult) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "leads.json", result.model_dump(mode="json"))
    to_leads_csv(out_dir / "leads.csv", result.leads, result.qualifications)
    to_drafts_json(out_dir / "drafts.json", result.drafts)
    to_drafts_csv(out_dir / "drafts.csv", result.drafts)


def load_leads(path: Path) -> list[Lead]:
    if not path.exists():
        raise ConfigError(f"Input file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Input file is not valid JSON: {path}") from exc
    if isinstance(data, dict):
        items = data.get("leads", [])
    elif isinstance(data, list):
        items = data
    else:
        raise ConfigError("Input JSON must be a list of leads or an object with a 'leads' key.")
    leads: list[Lead] = []
    for item in items:
        if not isinstance(item, dict):
            raise ConfigError("Each lead in the input file must be a JSON object.")
        leads.append(Lead.model_validate(item))
    return leads


def load_qualifications(path: Path) -> list[Qualification]:
    if not path.exists():
        raise ConfigError(f"Qualifications file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Qualifications file is not valid JSON: {path}") from exc
    if isinstance(data, dict):
        items = data.get("qualifications", [])
    elif isinstance(data, list):
        items = data
    else:
        raise ConfigError(
            "Qualifications JSON must be a list or an object with a 'qualifications' key."
        )
    qualifications: list[Qualification] = []
    for item in items:
        if not isinstance(item, dict):
            raise ConfigError("Each qualification must be a JSON object.")
        qualifications.append(Qualification.model_validate(item))
    return qualifications
