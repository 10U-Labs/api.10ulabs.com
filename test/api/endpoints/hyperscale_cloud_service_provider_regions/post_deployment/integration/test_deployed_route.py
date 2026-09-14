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


def test_a_region_that_is_not_there_answers_404_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = get_json(f"{stage_url}{REGIONS}/0", bearer)
    assert status == 404


def test_a_region_that_is_not_there_names_the_error_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = get_json(f"{stage_url}{REGIONS}/0", bearer)
    assert body["error"] == "No such hyperscale cloud service provider region"


def test_every_listed_region_is_served_at_its_own_url_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, listed = get_json(f"{stage_url}{REGIONS}", bearer)
    served = [get_json(f"{stage_url}{REGIONS}/{region['id']}", bearer) for region in listed]
    assert served == [(200, region) for region in listed]


PHOENIX = {"name": "us-west-2", "municipality": "Phoenix", "state": "AZ", "country": "US",
           "latitude": 33.4484, "longitude": -112.074}


def test_the_workflows_key_is_refused_a_region_correction_through_the_deployed_api(
    stage_url: str, put_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = put_json(f"{stage_url}{REGIONS}/0", PHOENIX, bearer)
    assert status == 403


def test_a_refused_correction_leaves_every_listed_region_as_it_was_through_the_deployed_api(
    stage_url: str,
    get_json: Callable[..., Tuple[int, Any]],
    put_json: Callable[..., Tuple[int, Any]],
    bearer: Dict[str, str],
) -> None:
    _, listed = get_json(f"{stage_url}{REGIONS}", bearer)
    refused = [put_json(f"{stage_url}{REGIONS}/{one['id']}", PHOENIX, bearer)[0] for one in listed]
    assert (refused, get_json(f"{stage_url}{REGIONS}", bearer)[1]) == ([403] * len(listed), listed)


def test_the_workflows_key_deletes_no_region_that_is_not_there_through_the_deployed_api(
    stage_url: str, delete_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = delete_json(f"{stage_url}{REGIONS}/0", bearer)
    assert status == 404


def test_a_deletion_of_a_region_that_is_not_there_names_the_error_through_the_deployed_api(
    stage_url: str, delete_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = delete_json(f"{stage_url}{REGIONS}/0", bearer)
    assert body["error"] == "No such hyperscale cloud service provider region"
