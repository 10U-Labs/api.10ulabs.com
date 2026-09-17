from typing import Dict, Optional, Tuple
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

CARRIERS = "https://api.10ulabs.com/carriers"
HIT = "Hit from cloudfront"


def _answered(headers: Optional[Dict[str, str]] = None) -> Tuple[int, str]:
    try:
        with urlopen(Request(CARRIERS, headers=headers or {}), timeout=10) as response:
            return int(response.status), str(response.headers.get("X-Cache"))
    except HTTPError as error:
        return error.code, str(error.headers.get("X-Cache"))


@pytest.fixture(scope="module", name="read_twice")
def read_twice_fixture(bearer: Dict[str, str]) -> Tuple[int, str]:
    _answered(bearer)
    return _answered(bearer)


def test_a_repeated_read_of_the_carriers_is_served_by_the_distribution(
    read_twice: Tuple[int, str]
) -> None:
    assert read_twice == (200, HIT)


@pytest.mark.usefixtures("read_twice")
def test_a_read_without_a_token_is_refused_though_the_carriers_are_cached() -> None:
    assert _answered()[0] == 401


@pytest.mark.usefixtures("read_twice")
def test_a_read_with_a_token_the_authorizer_does_not_know_is_refused_though_cached() -> None:
    assert _answered({"Authorization": "Bearer not-the-key"})[0] == 401
