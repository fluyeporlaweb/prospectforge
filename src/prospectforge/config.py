from __future__ import annotations

import os

from .errors import CapExceededError, ConfigError

DEFAULT_MAX_RESULTS = 25
MAX_LIVE_RESULTS = 500
SMOKE_MAX = 3
DEFAULT_MIN_SCORE = 60
DEFAULT_PROVIDER = "b2bsearch"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"

AFFILIATE_SIGNUP_URL = "https://www.apify.com?fpr=fplw"
APIFY_TOKEN_URL = AFFILIATE_SIGNUP_URL

B2BSEARCH_ACTOR_ID = "gZivd9twvcH2kwNQ3"
B2BSEARCH_ACTOR_NAME = "b2bsearch/b2b-leads-finder"
B2BSEARCH_ACTOR_URL = "https://apify.com/b2bsearch/b2b-leads-finder?fpr=fplw"

OLYMPUS_ACTOR_ID = "JA1e5BXb174wKCiqj"
OLYMPUS_ACTOR_NAME = "olympus/b2b-leads-finder"
OLYMPUS_ACTOR_URL = "https://apify.com/olympus/b2b-leads-finder?fpr=fplw"

PROVIDER_ACTOR_IDS = {
    "b2bsearch": B2BSEARCH_ACTOR_ID,
    "olympus": OLYMPUS_ACTOR_ID,
}


def resolve_max_results(value: int | None) -> int:
    """Return the effective live result count.

    An omitted value means DEFAULT_MAX_RESULTS. A provided value is used as-is
    after validation; it is never silently clamped upward.
    """
    if value is None:
        return DEFAULT_MAX_RESULTS
    if value < 1 or value > MAX_LIVE_RESULTS:
        raise CapExceededError(f"--max must be between 1 and {MAX_LIVE_RESULTS}; got {value}.")
    return value


def validate_min_score(value: int) -> int:
    if value < 0 or value > 100:
        raise ConfigError(f"--min-score must be between 0 and 100; got {value}.")
    return value


def get_apify_token() -> str | None:
    token = os.environ.get("APIFY_TOKEN", "").strip()
    return token or None


def get_openai_api_key() -> str | None:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    return key or None


def get_openai_base_url() -> str:
    return os.environ.get("OPENAI_BASE_URL", "").strip() or DEFAULT_OPENAI_BASE_URL


def get_default_model() -> str:
    return os.environ.get("PROSPECTFORGE_MODEL", "").strip() or DEFAULT_MODEL


def require_apify_token() -> str:
    token = get_apify_token()
    if token is None:
        raise ConfigError(
            "APIFY_TOKEN is not set. Export it before a live discover run, or use "
            f"--dry-run. Get a token at {APIFY_TOKEN_URL}"
        )
    return token
