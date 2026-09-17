from typing import Any, Callable, Dict, Optional, Tuple
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

API_NAME = "api.10ulabs.com"
COLLECTIONS = ["/carriers", "/hyperscale-cloud-service-provider-regions"]
HIT = "Hit from cloudfront"
UNKNOWN = {"Authorization": "Bearer not-the-key"}
RACK = "/rack-configurations"
SUBMISSION = {
    "device_id": "post-deployment-tests",
    "configuration": {"rackHeight": 12, "rackCount": 1, "placedParts": []},
}


def _answered(path: str, headers: Optional[Dict[str, str]] = None) -> Tuple[int, str]:
    request = Request(f"https://{API_NAME}{path}", headers=headers or {})
    try:
        with urlopen(request, timeout=10) as response:
            return int(response.status), str(response.headers.get("X-Cache"))
    except HTTPError as error:
        return error.code, str(error.headers.get("X-Cache"))


@pytest.fixture(scope="module", name="cached", params=COLLECTIONS)
def cached_fixture(
    request: pytest.FixtureRequest, bearer: Dict[str, str]
) -> Tuple[str, Tuple[int, str]]:
    collection = str(request.param)
    _answered(collection, bearer)
    return collection, _answered(collection, bearer)


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


@pytest.fixture(scope="module", name="stored_hash")
def stored_hash_fixture(post_json: Callable[..., Tuple[int, Dict[str, Any]]]) -> str:
    _, stored = post_json(f"https://{API_NAME}{RACK}", SUBMISSION)
    return str(stored["config_hash"])


@pytest.fixture(scope="module", name="read_back")
def read_back_fixture(
    stored_hash: str, get_json: Callable[[str], Tuple[int, Dict[str, Any]]]
) -> Tuple[int, Dict[str, Any]]:
    return get_json(f"https://{API_NAME}{RACK}/{stored_hash}")


def test_a_stored_configuration_is_read_back_through_the_name(
    read_back: Tuple[int, Dict[str, Any]]
) -> None:
    assert read_back[1]["configuration"] == SUBMISSION["configuration"]


@pytest.mark.usefixtures("read_back")
def test_a_repeated_read_of_a_stored_configuration_is_served_by_the_distribution(
    stored_hash: str
) -> None:
    assert _answered(f"{RACK}/{stored_hash}") == (200, HIT)
