from __future__ import annotations

import pytest

from prospectforge.config import (
    DEFAULT_MAX_RESULTS,
    MAX_LIVE_RESULTS,
    SMOKE_MAX,
    resolve_max_results,
)
from prospectforge.errors import CapExceededError


def test_default_max_is_25() -> None:
    assert DEFAULT_MAX_RESULTS == 25
    assert resolve_max_results(None) == 25


def test_user_max_is_not_clamped_upward() -> None:
    assert resolve_max_results(2) == 2
    assert resolve_max_results(1) == 1
    assert resolve_max_results(MAX_LIVE_RESULTS) == MAX_LIVE_RESULTS


@pytest.mark.parametrize("value", [0, -1, MAX_LIVE_RESULTS + 1, 10000])
def test_out_of_range_max_is_rejected(value: int) -> None:
    with pytest.raises(CapExceededError):
        resolve_max_results(value)


def test_smoke_cap_is_three() -> None:
    assert SMOKE_MAX == 3
