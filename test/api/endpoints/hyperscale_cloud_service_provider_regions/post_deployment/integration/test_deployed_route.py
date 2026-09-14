from typing import Any, Callable, Dict, Tuple

REGIONS = "/hyperscale-cloud-service-provider-regions"


def test_the_regions_are_listed_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = get_json(f"{stage_url}{REGIONS}", bearer)
    assert status == 200


def test_the_deployed_api_answers_a_list_of_regions(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = get_json(f"{stage_url}{REGIONS}", bearer)
    assert isinstance(body, list)


def test_the_regions_refuse_a_call_without_a_token_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]]
) -> None:
    status, _ = get_json(f"{stage_url}{REGIONS}")
    assert status == 401


def test_a_region_without_a_place_is_refused_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = post_json(f"{stage_url}{REGIONS}", {}, bearer)
    assert status == 400


def test_a_region_without_a_place_is_told_what_is_expected_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = post_json(f"{stage_url}{REGIONS}", {}, bearer)
    assert body["error"] == (
        'The body must be exactly '
        '{"name", "municipality", "state", "country", "latitude", "longitude"}'
    )
