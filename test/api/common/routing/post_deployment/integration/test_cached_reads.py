from typing import Any, Callable, Dict, Optional, Tuple
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

API_NAME = "api.10ulabs.com"
SYNTHESES = "/wan-syntheses"
COLLECTIONS = ["/carriers", "/hyperscale-cloud-service-provider-regions", SYNTHESES]
HIT = "Hit from cloudfront"
RE_READS = 5
UNKNOWN = {"Authorization": "Bearer not-the-key"}


def _answered(path: str, headers: Optional[Dict[str, str]] = None) -> Tuple[int, str]:
    request = Request(f"https://{API_NAME}{path}", headers=headers or {})
    try:
        with urlopen(request, timeout=10) as response:
            return int(response.status), str(response.headers.get("X-Cache"))
    except HTTPError as error:
        return error.code, str(error.headers.get("X-Cache"))


def _repeated(path: str, headers: Optional[Dict[str, str]] = None) -> Tuple[int, str]:
    answer = _answered(path, headers)
    for _ in range(RE_READS):
        if answer[1] == HIT:
            break
        answer = _answered(path, headers)
    return answer


@pytest.fixture(scope="module", name="cached", params=COLLECTIONS)
def cached_fixture(
    request: pytest.FixtureRequest, bearer: Dict[str, str]
) -> Tuple[str, Tuple[int, str]]:
    collection = str(request.param)
    return collection, _repeated(collection, bearer)


def test_a_repeated_read_of_a_cached_collection_is_served_by_the_distribution(
    cached: Tuple[str, Tuple[int, str]]
) -> None:
    assert cached[1] == (200, HIT)


def test_a_read_without_a_token_is_refused_though_the_collection_is_cached(
    cached: Tuple[str, Tuple[int, str]]
) -> None:
    assert _answered(cached[0])[0] == 401


def test_a_read_with_a_token_the_authorizer_does_not_know_is_refused_though_cached(
    cached: Tuple[str, Tuple[int, str]]
) -> None:
    assert _answered(cached[0], UNKNOWN)[0] == 401


@pytest.fixture(scope="module", name="finished")
def finished_fixture(
    get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> str:
    _, listed = get_json(f"https://{API_NAME}{SYNTHESES}", bearer)
    paths = [f"{SYNTHESES}/{one['id']}" for one in listed]
    return next(
        path for path in paths
        if get_json(f"https://{API_NAME}{path}", bearer)[1]["status"] == "success"
    )


def test_a_repeated_read_of_a_finished_synthesis_is_served_by_the_distribution(
    finished: str, bearer: Dict[str, str]
) -> None:
    assert _repeated(finished, bearer) == (200, HIT)


def test_the_wan_pops_of_a_finished_synthesis_are_served_through_the_name(
    finished: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    assert get_json(f"https://{API_NAME}{finished}/wan-pops", bearer)[0] == 200
