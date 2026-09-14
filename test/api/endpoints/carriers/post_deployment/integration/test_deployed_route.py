from typing import Any, Callable, Dict, Tuple


def test_the_carriers_are_listed_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = get_json(f"{stage_url}/carriers", bearer)
    assert status == 200


def test_the_deployed_api_answers_a_list_of_carriers(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = get_json(f"{stage_url}/carriers", bearer)
    assert isinstance(body, list)


def test_a_body_without_a_name_is_refused_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = post_json(f"{stage_url}/carriers", {}, bearer)
    assert status == 400


def test_a_body_without_a_name_is_told_what_is_expected_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = post_json(f"{stage_url}/carriers", {}, bearer)
    assert body["error"] == "The body must be exactly {\"name\"}"


def test_a_carrier_that_is_not_there_answers_404_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = get_json(f"{stage_url}/carriers/0", bearer)
    assert status == 404


def test_a_carrier_that_is_not_there_names_the_error_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = get_json(f"{stage_url}/carriers/0", bearer)
    assert body["error"] == "No such carrier"


def test_every_listed_carrier_is_served_at_its_own_url_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, listed = get_json(f"{stage_url}/carriers", bearer)
    served = [get_json(f"{stage_url}/carriers/{carrier['id']}", bearer) for carrier in listed]
    assert served == [(200, carrier) for carrier in listed]


def test_the_workflows_key_is_refused_a_rename_through_the_deployed_api(
    stage_url: str, put_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = put_json(f"{stage_url}/carriers/0", {"name": "nobody"}, bearer)
    assert status == 403


def test_the_workflows_key_deletes_no_carrier_that_is_not_there_through_the_deployed_api(
    stage_url: str, delete_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = delete_json(f"{stage_url}/carriers/0", bearer)
    assert status == 404


def test_a_deletion_of_a_carrier_that_is_not_there_names_the_error_through_the_deployed_api(
    stage_url: str, delete_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = delete_json(f"{stage_url}/carriers/0", bearer)
    assert body["error"] == "No such carrier"
