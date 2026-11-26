from __future__ import annotations

import re
from collections.abc import Iterable

from .errors import ConfigError
from .models import IcpFilters

ISO2_TO_NAME: dict[str, str] = {
    "es": "Spain",
    "us": "United States",
    "gb": "United Kingdom",
    "uk": "United Kingdom",
    "ie": "Ireland",
    "fr": "France",
    "de": "Germany",
    "it": "Italy",
    "pt": "Portugal",
    "nl": "Netherlands",
    "be": "Belgium",
    "ch": "Switzerland",
    "at": "Austria",
    "se": "Sweden",
    "no": "Norway",
    "dk": "Denmark",
    "fi": "Finland",
    "pl": "Poland",
    "cz": "Czech Republic",
    "ro": "Romania",
    "gr": "Greece",
    "tr": "Turkey",
    "ca": "Canada",
    "mx": "Mexico",
    "br": "Brazil",
    "ar": "Argentina",
    "cl": "Chile",
    "co": "Colombia",
    "au": "Australia",
    "nz": "New Zealand",
    "in": "India",
    "sg": "Singapore",
    "jp": "Japan",
    "kr": "South Korea",
    "cn": "China",
    "ae": "United Arab Emirates",
    "il": "Israel",
    "za": "South Africa",
}

NAME_TO_ISO2: dict[str, str] = {name.lower(): code for code, name in ISO2_TO_NAME.items()}
NAME_TO_ISO2["united states of america"] = "us"
NAME_TO_ISO2["usa"] = "us"

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "them",
    "they",
    "this",
    "to",
    "we",
    "who",
    "with",
    "you",
    "your",
    "small",
    "large",
    "companies",
    "company",
    "business",
    "businesses",
}

TITLE_WORDS = {
    "founder",
    "co-founder",
    "cofounder",
    "owner",
    "ceo",
    "cto",
    "cfo",
    "coo",
    "cmo",
    "vp",
    "vice president",
    "head",
    "director",
    "manager",
    "lead",
    "engineer",
    "developer",
    "marketing",
    "sales",
}

SENIORITY_ENUM_MAP: dict[str, str] = {
    "owner": "owner",
    "founder": "founder",
    "co-founder": "founder",
    "cofounder": "founder",
    "c_suite": "c_suite",
    "c-suite": "c_suite",
    "csuite": "c_suite",
    "cxo": "c_suite",
    "ceo": "c_suite",
    "cto": "c_suite",
    "cfo": "c_suite",
    "coo": "c_suite",
    "cmo": "c_suite",
    "chief": "c_suite",
    "partner": "partner",
    "vp": "vp",
    "vice president": "vp",
    "head": "head",
    "head of": "head",
    "director": "director",
    "manager": "manager",
    "senior": "senior",
    "entry": "entry",
    "intern": "intern",
}

OLYMPUS_SENIORITY_ENUMS = {
    "owner",
    "founder",
    "c_suite",
    "partner",
    "vp",
    "head",
    "director",
    "manager",
    "senior",
    "entry",
    "intern",
}


def _normalize_token(token: str) -> str:
    token = token.strip().lower()
    token = token.strip(".,;:!?()[]{}\"'")
    if len(token) > 4 and token.endswith("ies"):
        token = token[:-3] + "y"
    elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        token = token[:-1]
    return token


def extract_keywords(text: str, limit: int | None = None) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+'-]+", text.lower())
    seen: list[str] = []
    for token in tokens:
        if token in STOPWORDS:
            continue
        normalized = _normalize_token(token)
        if len(normalized) < 3 or normalized in STOPWORDS:
            continue
        if normalized not in seen:
            seen.append(normalized)
    if limit is not None:
        return seen[:limit]
    return seen


def normalize_country_code(value: str) -> str:
    raw = value.strip()
    if not raw:
        raise ConfigError("Country value cannot be empty.")
    lowered = raw.lower()
    if len(lowered) == 2:
        return lowered
    if lowered in NAME_TO_ISO2:
        return NAME_TO_ISO2[lowered]
    raise ConfigError(f"Unknown country {value!r}. Use an ISO-2 code such as 'es' or 'us'.")


def country_name(iso2: str) -> str:
    code = normalize_country_code(iso2)
    try:
        return ISO2_TO_NAME[code]
    except KeyError as exc:
        raise ConfigError(
            f"Country code {iso2!r} is not in the built-in olympus name map. "
            "Use a common ISO-2 code or the b2bsearch provider."
        ) from exc


def to_olympus_seniority(values: Iterable[str]) -> list[str]:
    mapped: list[str] = []
    for value in values:
        for part in re.split(r"[,/]", value):
            key = part.strip().lower()
            enum = SENIORITY_ENUM_MAP.get(key)
            if enum is None:
                for phrase, candidate in SENIORITY_ENUM_MAP.items():
                    if key.startswith(phrase):
                        enum = candidate
                        break
            if enum and enum in OLYMPUS_SENIORITY_ENUMS and enum not in mapped:
                mapped.append(enum)
    return mapped


def detect_titles(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for title in sorted(TITLE_WORDS):
        if re.search(rf"\b{re.escape(title)}s?\b", lowered) and title not in found:
            found.append(title)
    return found


def detect_countries(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for name, code in NAME_TO_ISO2.items():
        if re.search(rf"\b{re.escape(name)}\b", lowered) and code not in found:
            found.append(code)
    return found


def parse_icp(text: str) -> IcpFilters:
    """Best-effort ICP text parser used by the library and tests."""
    keywords = extract_keywords(text)
    return IcpFilters(
        titles=detect_titles(text),
        countries=detect_countries(text),
        keywords=keywords,
    )
