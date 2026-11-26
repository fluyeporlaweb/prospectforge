# Contributing to prospectforge

Thanks for helping improve `prospectforge`. This project is a small, safety-first B2B lead pipeline: it discovers contacts, qualifies them against an ICP, and drafts outreach, but it never sends email. Please keep that boundary intact.

## Development setup

```bash
git clone https://github.com/fluyeporlaweb/prospectforge.git
cd prospectforge
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

Python 3.11 or newer is required.

## Checks

Run these before opening a pull request:

```bash
ruff check .
mypy src
pytest -m "not apify" -q
```

The default test suite is fully offline and does not need any credentials. Keep it that way: new tests should use fixtures, fakes, or mocks rather than live services.

## Regenerating images

The README images are generated, not hand-edited. Install Pillow in your virtual environment and run:

```bash
pip install pillow
python scripts/generate_assets.py
```

This rewrites `assets/banner.png` (1280x640) and `assets/architecture.png` (1280x720). Review both images before committing.

## Live smoke tests

A small live smoke test is marked `apify`. It is skipped unless `APIFY_TOKEN` is present and it is capped at 2-3 results. Only run it when you have explicitly chosen to spend Apify credits:

```bash
APIFY_TOKEN=... pytest -m apify -q
```

Do not add live smoke tests to CI. Do not print tokens, request headers, or personal data in test output.

## Code guidelines

- Keep `src/prospectforge/apify_client.py` as the only module that imports the Apify client.
- Preserve dry-run behavior: `--dry-run` must not contact Apify or an LLM.
- Keep the no-send guarantee. Do not add SMTP, mailbox, email API, scheduling, or auto-send code.
- Use pydantic v2 models for data that crosses module boundaries.
- Prefer small, typed functions. `mypy` runs with `disallow_untyped_defs`.
- Keep provider-specific mapping in the provider adapter and preserve unknown payload fields in `raw_source`.
- Add or update tests with every behavior change.

## Commit messages

Use conventional commits:

```text
feat: add olympus provider filter warnings
fix: keep dry-run from creating an Apify client
docs: clarify GDPR responsibility in the README
test: cover malformed LLM JSON fallback
chore: update dev dependencies
```

Keep commits focused. Explain the why in the body when the change is not obvious.

## Secrets and personal data

Never commit:

- `.env` files or real API keys.
- `APIFY_TOKEN`, `OPENAI_API_KEY`, or any other credential.
- Real lead data, email addresses, phone numbers, or private datasets.
- `.venv`, caches, build output, or files under `out/`.

Use `.env.example` for variable names only. If you accidentally expose a secret, rotate it immediately and tell the maintainers.

## Pull requests

- Describe the problem and the change.
- List the checks you ran.
- Call out any behavior change, especially around network access, credentials, caps, or output files.
- Keep the scope tight. Separate refactors from behavior changes.
- By contributing, you agree that your contribution is licensed under the MIT License.
