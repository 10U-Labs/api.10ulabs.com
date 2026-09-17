import time
from typing import Any, Callable, Dict, Iterator, List, NamedTuple, Optional, Tuple
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

API_NAME = "api.10ulabs.com"
COLLECTIONS = ["/carriers", "/hyperscale-cloud-service-provider-regions"]
HIT = "Hit from cloudfront"
RE_READS = 5
UNKNOWN = {"Authorization": "Bearer not-the-key"}
RACK = "/rack-configurations"
SUBMISSION = {
    "device_id": "post-deployment-tests",
    "configuration": {"rackHeight": 12, "rackCount": 1, "placedParts": []},
}
SYNTHESES = "/wan-syntheses"
STATUSES = ("creating", "synthesizing", "success")
RUNNING = STATUSES[:2]
POLLS = 96
PAUSE = 10
ASHBURN = {"municipality": "Ashburn", "state": "VA", "country": "United States",
           "latitude": 39.0438, "longitude": -77.4874}
SALT_LAKE_CITY = {"municipality": "Salt Lake City", "state": "UT", "country": "United States",
                  "latitude": 40.7608, "longitude": -111.891}
COLUMBUS = {"municipality": "Columbus", "state": "OH", "country": "United States",
            "latitude": 39.9612, "longitude": -82.9988}
RUN = {
    "label": "post-deployment-tests",
    "wan_pop_count": {"min": 2, "max": 2},
    "backbone_number_of_diverse_circuits": 2,
    "homing_degree": 2,
    "convergence_promotion": False,
    "knobs": {"backbone_coverage_target_miles": 1090},
    "settings": {
        "bytes_per_wan_pop_combination": 160, "wan_pop_search_memory_share": 0.6,
        "compass_sector_count": 8,
    },
    "sites": [
        {"name": "Ashburn", **ASHBURN, "exempt_from_distance_constraint": False},
        {"name": "Salt Lake City", **SALT_LAKE_CITY, "exempt_from_distance_constraint": False},
    ],
    "hyperscale_cloud_service_provider_regions": [{"name": "Provider A", **COLUMBUS}],
    "off_net": [],
    "forced_wan_pops": ["Ashburn, VA", "Salt Lake City, UT"],
    "forced_circuits": [],
    "forced_homes": [],
    "prohibited_wan_pops": [],
    "prohibited_circuits": [],
    "degree_exempt_wan_pops": [],
}


class Watched(NamedTuple):
    path: str
    seen: List[str]
    pops_before: int
    pops_after: int


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
    assert _repeated(f"{RACK}/{stored_hash}") == (200, HIT)


@pytest.fixture(scope="module", name="synthesis")
def synthesis_fixture(
    post_json: Callable[..., Tuple[int, Dict[str, Any]]],
    get_json: Callable[..., Tuple[int, Dict[str, Any]]],
    delete_json: Callable[..., Tuple[int, Any]],
    bearer: Dict[str, str],
) -> Iterator[Watched]:
    status, created = post_json(f"https://{API_NAME}{SYNTHESES}", RUN, bearer)
    if status != 201:
        raise RuntimeError(f"the synthesis was refused with {status}: {created}")
    path = f"{SYNTHESES}/{created['id']}"
    url = f"https://{API_NAME}{path}"
    try:
        pops_before = get_json(f"{url}/wan-pops", bearer)[0]
        seen = [str(created["status"])]
        for _ in range(POLLS):
            if seen[-1] not in RUNNING:
                break
            time.sleep(PAUSE)
            marked = str(get_json(url, bearer)[1]["status"])
            if marked != seen[-1]:
                seen.append(marked)
        yield Watched(path, seen, pops_before, get_json(f"{url}/wan-pops", bearer)[0])
    finally:
        delete_json(url, bearer)


def test_a_synthesis_created_through_the_name_ends_in_success(synthesis: Watched) -> None:
    assert synthesis.seen[-1] == "success"


def test_the_status_of_a_synthesis_only_advances_as_the_synthesizer_runs(
    synthesis: Watched
) -> None:
    assert synthesis.seen == [one for one in STATUSES if one in synthesis.seen]


def test_the_wan_pops_of_a_synthesis_answer_404_until_it_succeeds(synthesis: Watched) -> None:
    assert (synthesis.pops_before, synthesis.pops_after) == (404, 200)


def test_a_repeated_read_of_a_finished_synthesis_is_served_by_the_distribution(
    synthesis: Watched, bearer: Dict[str, str]
) -> None:
    assert _repeated(synthesis.path, bearer) == (200, HIT)
