from typing import Any, Callable, Dict, List, Tuple


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


def test_the_pops_of_a_carrier_that_is_not_there_answer_404_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = get_json(f"{stage_url}/carriers/0/pops", bearer)
    assert status == 404


def test_the_pops_of_a_carrier_that_is_not_there_name_the_error_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = get_json(f"{stage_url}/carriers/0/pops", bearer)
    assert body["error"] == "No such carrier"


def test_every_listed_carrier_answers_a_list_of_pops_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, listed = get_json(f"{stage_url}/carriers", bearer)
    answered = [get_json(f"{stage_url}/carriers/{one['id']}/pops", bearer) for one in listed]
    assert [(status, type(pops)) for status, pops in answered] == [(200, list)] * len(listed)


BOISE = {"municipality": "Boise", "state": "ID", "country": "US",
         "latitude": 43.615, "longitude": -116.2023}


def test_a_pop_without_a_place_is_refused_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = post_json(f"{stage_url}/carriers/0/pops", {}, bearer)
    assert status == 400


def test_a_pop_without_a_place_is_told_what_is_expected_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = post_json(f"{stage_url}/carriers/0/pops", {}, bearer)
    assert body["error"] == (
        'The body must be exactly {"municipality", "state", "country", "latitude", "longitude"}'
    )


def test_a_pop_for_a_carrier_that_is_not_there_answers_404_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = post_json(f"{stage_url}/carriers/0/pops", BOISE, bearer)
    assert status == 404


def test_a_pop_for_a_carrier_that_is_not_there_names_the_error_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = post_json(f"{stage_url}/carriers/0/pops", BOISE, bearer)
    assert body["error"] == "No such carrier"


def test_a_pop_of_a_carrier_that_is_not_there_answers_404_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = get_json(f"{stage_url}/carriers/0/pops/0", bearer)
    assert status == 404


def test_a_pop_of_a_carrier_that_is_not_there_names_the_carrier_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = get_json(f"{stage_url}/carriers/0/pops/0", bearer)
    assert body["error"] == "No such carrier"


def test_no_listed_carrier_has_a_pop_zero_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, listed = get_json(f"{stage_url}/carriers", bearer)
    answered = [get_json(f"{stage_url}/carriers/{one['id']}/pops/0", bearer) for one in listed]
    assert answered == [(404, {"error": "No such pop"})] * len(listed)


def _first_pops(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> List[Tuple[str, Dict[str, Any]]]:
    _, listed = get_json(f"{stage_url}/carriers", bearer)
    return [
        (f"{stage_url}/carriers/{one['id']}/pops/{pop['id']}", pop)
        for one in listed
        for pop in get_json(f"{stage_url}/carriers/{one['id']}/pops", bearer)[1][:1]
    ]


def test_the_first_pop_of_every_listed_carrier_is_served_at_its_own_url_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    firsts = _first_pops(stage_url, get_json, bearer)
    assert [get_json(url, bearer) for url, _ in firsts] == [(200, pop) for _, pop in firsts]


def test_the_workflows_key_is_refused_a_pop_correction_through_the_deployed_api(
    stage_url: str, put_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = put_json(f"{stage_url}/carriers/0/pops/0", BOISE, bearer)
    assert status == 403


def test_a_refused_correction_leaves_the_first_pop_of_every_listed_carrier_as_it_was(
    stage_url: str,
    get_json: Callable[..., Tuple[int, Any]],
    put_json: Callable[..., Tuple[int, Any]],
    bearer: Dict[str, str],
) -> None:
    firsts = _first_pops(stage_url, get_json, bearer)
    refused = [put_json(url, BOISE, bearer)[0] for url, _ in firsts]
    assert (refused, [get_json(url, bearer)[1] for url, _ in firsts]) == (
        [403] * len(firsts), [pop for _, pop in firsts]
    )
