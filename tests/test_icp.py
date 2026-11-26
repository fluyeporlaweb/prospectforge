from __future__ import annotations

import pytest

from prospectforge.errors import ConfigError
from prospectforge.icp import (
    country_name,
    extract_keywords,
    normalize_country_code,
    parse_icp,
    to_olympus_seniority,
)


def test_extract_keywords_normalizes_plurals_and_stopwords() -> None:
    keywords = extract_keywords("Founders at small software companies in Spain")
    assert "founder" in keywords
    assert "software" in keywords
    assert "spain" in keywords
    assert "small" not in keywords
    assert "companies" not in keywords


def test_parse_icp_detects_country_and_title() -> None:
    filters = parse_icp("Founders at software companies in Spain")
    assert filters.countries == ["es"]
    assert "founder" in filters.titles
    assert "software" in filters.keywords


def test_country_normalization() -> None:
    assert normalize_country_code("ES") == "es"
    assert normalize_country_code("Spain") == "es"
    assert normalize_country_code("United States") == "us"
    assert country_name("es") == "Spain"
    with pytest.raises(ConfigError):
        normalize_country_code("Neverland")


def test_olympus_seniority_mapping_drops_unknown() -> None:
    mapped = to_olympus_seniority(["founder", "CEO", "wizard", "head of sales"])
    assert mapped == ["founder", "c_suite", "head"]
