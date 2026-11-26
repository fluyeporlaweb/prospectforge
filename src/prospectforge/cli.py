from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .config import (
    AFFILIATE_SIGNUP_URL,
    DEFAULT_MAX_RESULTS,
    DEFAULT_MIN_SCORE,
    require_apify_token,
    resolve_max_results,
    validate_min_score,
)
from .draft import build_drafter
from .errors import CapExceededError, ConfigError, ProspectforgeError
from .export import (
    export_result,
    load_leads,
    load_qualifications,
    to_drafts_csv,
    to_drafts_json,
    to_leads_csv,
    to_leads_json,
    write_json,
)
from .icp import normalize_country_code
from .models import IcpFilters, PipelineResult
from .pipeline import Pipeline, make_llm_client
from .qualify import build_qualifier

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help=(
        "Open-source B2B lead pipeline: discover contacts with Apify, qualify them "
        "against your ICP, and draft outreach. Never sends email."
    ),
)

LIST_OPTIONS = {
    "titles": "Job titles to target (repeatable).",
    "countries": "Countries as ISO-2 codes, e.g. es or us (repeatable).",
    "departments": "Departments to target (repeatable).",
    "seniority": "Seniority levels (repeatable).",
    "industries": "Industries or free-text industry keywords (repeatable).",
    "keywords": "Extra targeting keywords (repeatable).",
    "domains": "Company domains to target (repeatable).",
    "exclude_domains": "Company domains to exclude (repeatable).",
    "cities": "Cities to target (repeatable).",
    "exclude_titles": "Job titles to exclude (repeatable).",
}


def _fail(exc: ProspectforgeError) -> None:
    typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
    code = 2 if isinstance(exc, ConfigError) else 1
    raise typer.Exit(code=code)


def _resolve_out_file(path: Path, output_format: str) -> Path:
    if path.exists() and path.is_dir():
        return path / f"leads.{output_format}"
    if path.suffix == "":
        return path / f"leads.{output_format}"
    return path


def _build_filters(
    *,
    titles: list[str] | None,
    countries: list[str] | None,
    departments: list[str] | None,
    seniority: list[str] | None,
    industries: list[str] | None,
    keywords: list[str] | None,
    domains: list[str] | None,
    exclude_domains: list[str] | None,
    cities: list[str] | None,
    exclude_titles: list[str] | None,
    company_size_min: int | None,
    company_size_max: int | None,
) -> IcpFilters:
    normalized_countries = [normalize_country_code(code) for code in (countries or [])]
    return IcpFilters(
        titles=titles or [],
        exclude_titles=exclude_titles or [],
        departments=departments or [],
        seniority=seniority or [],
        countries=normalized_countries,
        cities=cities or [],
        industries=industries or [],
        keywords=keywords or [],
        company_domains=domains or [],
        exclude_domains=exclude_domains or [],
        company_size_min=company_size_min,
        company_size_max=company_size_max,
    )


def _print_result_summary(result: PipelineResult, out_dir: Path) -> None:
    summary = result.summary
    typer.echo(
        f"Discovered {summary.get('discovered', 0)} leads, "
        f"qualified {summary.get('qualified', 0)}, "
        f"drafted {summary.get('drafted', 0)}."
    )
    verdicts = summary.get("by_verdict", {})
    typer.echo(
        "Verdicts: "
        + ", ".join(f"{name}={verdicts.get(name, 0)}" for name in ("strong", "ok", "weak", "bad"))
    )
    typer.echo(f"LLM used: {summary.get('llm_used')} (dry_run={summary.get('dry_run')})")
    typer.echo(f"Wrote {out_dir / 'leads.json'}, {out_dir / 'leads.csv'}, and drafts.")


@app.callback(invoke_without_command=True)
def main(
    version: Annotated[
        bool,
        typer.Option("--version", help="Show the installed version and exit."),
    ] = False,
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command()
def discover(
    titles: Annotated[
        list[str] | None, typer.Option("--titles", help=LIST_OPTIONS["titles"])
    ] = None,
    countries: Annotated[
        list[str] | None, typer.Option("--countries", help=LIST_OPTIONS["countries"])
    ] = None,
    departments: Annotated[
        list[str] | None, typer.Option("--departments", help=LIST_OPTIONS["departments"])
    ] = None,
    seniority: Annotated[
        list[str] | None, typer.Option("--seniority", help=LIST_OPTIONS["seniority"])
    ] = None,
    industries: Annotated[
        list[str] | None, typer.Option("--industries", help=LIST_OPTIONS["industries"])
    ] = None,
    keywords: Annotated[
        list[str] | None, typer.Option("--keywords", help=LIST_OPTIONS["keywords"])
    ] = None,
    domains: Annotated[
        list[str] | None, typer.Option("--domains", help=LIST_OPTIONS["domains"])
    ] = None,
    exclude_domains: Annotated[
        list[str] | None,
        typer.Option("--exclude-domains", help=LIST_OPTIONS["exclude_domains"]),
    ] = None,
    cities: Annotated[
        list[str] | None, typer.Option("--cities", help=LIST_OPTIONS["cities"])
    ] = None,
    exclude_titles: Annotated[
        list[str] | None,
        typer.Option("--exclude-titles", help=LIST_OPTIONS["exclude_titles"]),
    ] = None,
    company_size_min: Annotated[
        int | None, typer.Option("--company-size-min", help="Minimum company headcount.")
    ] = None,
    company_size_max: Annotated[
        int | None, typer.Option("--company-size-max", help="Maximum company headcount.")
    ] = None,
    provider: Annotated[
        str, typer.Option("--provider", help="Lead provider: b2bsearch (default) or olympus.")
    ] = "b2bsearch",
    max_results: Annotated[
        int, typer.Option("--max", help="Maximum leads (1-500, default 25).")
    ] = DEFAULT_MAX_RESULTS,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Print the actor input JSON and exit without calling Apify."
        ),
    ] = False,
    out: Annotated[Path, typer.Option("--out", help="Output file or directory.")] = Path(
        "out/leads.json"
    ),
    output_format: Annotated[
        str, typer.Option("--format", help="Output format: json or csv.")
    ] = "json",
    email_type: Annotated[
        str, typer.Option("--email-type", help="b2bsearch email filter: any, work or personal.")
    ] = "any",
) -> None:
    """Discover leads with an Apify Actor, or print the actor input in dry-run mode."""
    try:
        effective_max = resolve_max_results(max_results)
        filters = _build_filters(
            titles=titles,
            countries=countries,
            departments=departments,
            seniority=seniority,
            industries=industries,
            keywords=keywords,
            domains=domains,
            exclude_domains=exclude_domains,
            cities=cities,
            exclude_titles=exclude_titles,
            company_size_min=company_size_min,
            company_size_max=company_size_max,
        )
        from .discover import get_provider

        provider_obj = get_provider(provider)
        actor_input = provider_obj.build_input(
            filters,
            effective_max,
            email_type=email_type,
        )
        if dry_run:
            typer.echo(json.dumps(actor_input, indent=2, ensure_ascii=False))
            return
        require_apify_token()
        raw_items = provider_obj.run(actor_input, max_results=effective_max)
        leads = [provider_obj.normalize(raw) for raw in raw_items[:effective_max]]
        out_path = _resolve_out_file(out, output_format)
        if output_format == "csv":
            to_leads_csv(out_path, leads)
        else:
            to_leads_json(out_path, leads)
        typer.echo(f"Wrote {len(leads)} leads to {out_path}")
        typer.echo(f"Apify signup (affiliate): {AFFILIATE_SIGNUP_URL}")
    except (CapExceededError, ConfigError) as exc:
        _fail(exc)
    except ProspectforgeError as exc:
        _fail(exc)


@app.command()
def qualify(
    input_path: Annotated[Path, typer.Option("--input", help="Input leads JSON file.")],
    product: Annotated[str, typer.Option("--product", help="What you sell, one or two sentences.")],
    icp: Annotated[str, typer.Option("--icp", help="Ideal customer profile description.")],
    min_score: Annotated[
        int, typer.Option("--min-score", help="Minimum score considered a fit (0-100).")
    ] = DEFAULT_MIN_SCORE,
    model: Annotated[
        str | None, typer.Option("--model", help="OpenAI-compatible model name.")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Qualify only the first lead and print JSON.")
    ] = False,
    out: Annotated[Path, typer.Option("--out", help="Output directory.")] = Path("out"),
) -> None:
    """Qualify leads against a product and ICP (heuristic without an LLM key)."""
    try:
        threshold = validate_min_score(min_score)
        leads = load_leads(input_path)
        client = make_llm_client(model, dry_run)
        qualifier = build_qualifier(client)
        if dry_run:
            if not leads:
                typer.echo("[]")
                return
            result = qualifier.qualify(leads[0], product, icp)
            typer.echo(result.model_dump_json(indent=2))
            return
        qualifications = [qualifier.qualify(lead, product, icp) for lead in leads]
        write_json(
            out / "qualifications.json",
            [qualification.model_dump(mode="json") for qualification in qualifications],
        )
        fit = sum(1 for qualification in qualifications if qualification.score >= threshold)
        typer.echo(f"Wrote {len(qualifications)} qualifications to {out / 'qualifications.json'}")
        typer.echo(f"{fit} lead(s) scored >= {threshold}.")
    except (CapExceededError, ConfigError) as exc:
        _fail(exc)
    except ProspectforgeError as exc:
        _fail(exc)


@app.command()
def draft(
    input_path: Annotated[Path, typer.Option("--input", help="Input leads JSON file.")],
    qualifications_path: Annotated[
        Path, typer.Option("--qualifications", help="Qualifications JSON file.")
    ],
    product: Annotated[str, typer.Option("--product", help="What you sell.")],
    model: Annotated[
        str | None, typer.Option("--model", help="OpenAI-compatible model name.")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Draft only the first eligible lead and print JSON.")
    ] = False,
    out: Annotated[Path, typer.Option("--out", help="Output directory.")] = Path("out"),
) -> None:
    """Draft personalized outreach for qualified leads. Never sends email."""
    try:
        leads = load_leads(input_path)
        qualifications = load_qualifications(qualifications_path)
        by_key = {qualification.lead_key: qualification for qualification in qualifications}
        client = make_llm_client(model, dry_run)
        drafter = build_drafter(client)
        drafts = []
        for lead in leads:
            qualification = by_key.get(lead.key)
            if qualification is None or not lead.email:
                continue
            drafts.append(drafter.draft(lead, qualification, product))
        if dry_run:
            if not drafts:
                typer.echo("[]")
                return
            typer.echo(drafts[0].model_dump_json(indent=2))
            return
        to_drafts_json(out / "drafts.json", drafts)
        to_drafts_csv(out / "drafts.csv", drafts)
        typer.echo(f"Wrote {len(drafts)} drafts to {out / 'drafts.json'}")
    except (CapExceededError, ConfigError) as exc:
        _fail(exc)
    except ProspectforgeError as exc:
        _fail(exc)


@app.command()
def run(
    product: Annotated[str, typer.Option("--product", help="What you sell.")],
    icp: Annotated[str, typer.Option("--icp", help="Ideal customer profile description.")],
    input_path: Annotated[
        Path | None,
        typer.Option("--input", help="Use a local leads JSON file instead of calling Apify."),
    ] = None,
    live: Annotated[
        bool,
        typer.Option(
            "--live",
            help="Allow a real Apify run (spends credits). Needed when --input is absent.",
        ),
    ] = False,
    titles: Annotated[
        list[str] | None, typer.Option("--titles", help=LIST_OPTIONS["titles"])
    ] = None,
    countries: Annotated[
        list[str] | None, typer.Option("--countries", help=LIST_OPTIONS["countries"])
    ] = None,
    departments: Annotated[
        list[str] | None, typer.Option("--departments", help=LIST_OPTIONS["departments"])
    ] = None,
    seniority: Annotated[
        list[str] | None, typer.Option("--seniority", help=LIST_OPTIONS["seniority"])
    ] = None,
    industries: Annotated[
        list[str] | None, typer.Option("--industries", help=LIST_OPTIONS["industries"])
    ] = None,
    keywords: Annotated[
        list[str] | None, typer.Option("--keywords", help=LIST_OPTIONS["keywords"])
    ] = None,
    domains: Annotated[
        list[str] | None, typer.Option("--domains", help=LIST_OPTIONS["domains"])
    ] = None,
    exclude_domains: Annotated[
        list[str] | None,
        typer.Option("--exclude-domains", help=LIST_OPTIONS["exclude_domains"]),
    ] = None,
    cities: Annotated[
        list[str] | None, typer.Option("--cities", help=LIST_OPTIONS["cities"])
    ] = None,
    exclude_titles: Annotated[
        list[str] | None,
        typer.Option("--exclude-titles", help=LIST_OPTIONS["exclude_titles"]),
    ] = None,
    company_size_min: Annotated[
        int | None, typer.Option("--company-size-min", help="Minimum company headcount.")
    ] = None,
    company_size_max: Annotated[
        int | None, typer.Option("--company-size-max", help="Maximum company headcount.")
    ] = None,
    provider: Annotated[
        str, typer.Option("--provider", help="Lead provider: b2bsearch (default) or olympus.")
    ] = "b2bsearch",
    max_results: Annotated[
        int, typer.Option("--max", help="Maximum leads (1-500, default 25).")
    ] = DEFAULT_MAX_RESULTS,
    email_type: Annotated[
        str, typer.Option("--email-type", help="b2bsearch email filter: any, work or personal.")
    ] = "any",
    min_score: Annotated[
        int, typer.Option("--min-score", help="Minimum score required for drafting (0-100).")
    ] = DEFAULT_MIN_SCORE,
    model: Annotated[
        str | None, typer.Option("--model", help="OpenAI-compatible model name.")
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="No network calls: use heuristic qualification/drafting and export locally.",
        ),
    ] = False,
    out: Annotated[Path, typer.Option("--out", help="Output directory.")] = Path("out"),
    output_format: Annotated[
        str, typer.Option("--format", help="Preferred format hint; both JSON and CSV are written.")
    ] = "json",
) -> None:
    """Run discover (or --input), qualify, draft and export. Live Apify needs --live."""
    try:
        effective_max = resolve_max_results(max_results)
        validate_min_score(min_score)
        if input_path is None and not live:
            typer.secho(
                "Refusing to start a paid Apify run. Pass --live to allow it, or pass "
                "--input with a local leads file.",
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(code=2)
        if input_path is None:
            require_apify_token()
            leads = None
        else:
            leads = load_leads(input_path)
        filters = _build_filters(
            titles=titles,
            countries=countries,
            departments=departments,
            seniority=seniority,
            industries=industries,
            keywords=keywords,
            domains=domains,
            exclude_domains=exclude_domains,
            cities=cities,
            exclude_titles=exclude_titles,
            company_size_min=company_size_min,
            company_size_max=company_size_max,
        )
        pipeline = Pipeline(
            product=product,
            icp=icp,
            provider=provider,
            filters=filters,
            max_results=effective_max,
            min_score=min_score,
            model=model,
            dry_run=dry_run,
            email_type=email_type,
        )
        result = pipeline.run(leads)
        export_result(out, result)
        _print_result_summary(result, out)
    except (CapExceededError, ConfigError) as exc:
        _fail(exc)
    except ProspectforgeError as exc:
        _fail(exc)
