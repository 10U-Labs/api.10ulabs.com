from typing import Any, Callable, Dict, List, Tuple

import pytest

THROUGH_THE_NAME = "https://api.10ulabs.com/carriers/0"
MEMBERS = ["pops", "fiber-segments"]
MISSING = dict(zip(MEMBERS, ["No such pop", "No such fiber segment"]))
BOISE = {"municipality": "Boise", "state": "ID", "country": "US",
         "latitude": 43.615, "longitude": -116.2023}
DEN_SLC = {"a_municipality": "Denver", "a_state": "CO",
           "z_municipality": "Salt Lake City", "z_state": "UT", "submarine": False}
CORRECTION = dict(zip(MEMBERS, [BOISE, DEN_SLC]))


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


def test_a_carrier_that_is_not_there_answers_404_through_the_name(
    get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = get_json(THROUGH_THE_NAME, bearer)
    assert status == 404


def test_a_carrier_that_is_not_there_keeps_its_own_json_through_the_name(
    get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = get_json(THROUGH_THE_NAME, bearer)
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


@pytest.mark.parametrize("members", MEMBERS)
def test_a_member_of_a_carrier_that_is_not_there_answers_404_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str],
    members: str,
) -> None:
    status, _ = get_json(f"{stage_url}/carriers/0/{members}/0", bearer)
    assert status == 404


@pytest.mark.parametrize("members", MEMBERS)
def test_a_member_of_a_carrier_that_is_not_there_names_the_carrier_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str],
    members: str,
) -> None:
    _, body = get_json(f"{stage_url}/carriers/0/{members}/0", bearer)
    assert body["error"] == "No such carrier"


@pytest.mark.parametrize("members", MEMBERS)
def test_no_listed_carrier_has_a_member_zero_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str],
    members: str,
) -> None:
    _, listed = get_json(f"{stage_url}/carriers", bearer)
    answered = [get_json(f"{stage_url}/carriers/{one['id']}/{members}/0", bearer) for one in listed]
    assert answered == [(404, {"error": MISSING[members]})] * len(listed)


def _firsts(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str], members: str
) -> List[Tuple[str, Dict[str, Any]]]:
    _, listed = get_json(f"{stage_url}/carriers", bearer)
    return [
        (f"{stage_url}/carriers/{one['id']}/{members}/{member['id']}", member)
        for one in listed
        for member in get_json(f"{stage_url}/carriers/{one['id']}/{members}", bearer)[1][:1]
    ]


@pytest.mark.parametrize("members", MEMBERS)
def test_the_first_member_of_every_listed_carrier_is_served_at_its_own_url_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str],
    members: str,
) -> None:
    firsts = _firsts(stage_url, get_json, bearer, members)
    assert [get_json(url, bearer) for url, _ in firsts] == [(200, one) for _, one in firsts]


@pytest.mark.parametrize("members", MEMBERS)
def test_the_workflows_key_is_refused_a_member_correction_through_the_deployed_api(
    stage_url: str, put_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str],
    members: str,
) -> None:
    status, _ = put_json(f"{stage_url}/carriers/0/{members}/0", CORRECTION[members], bearer)
    assert status == 403


@pytest.mark.parametrize("members", MEMBERS)
def test_a_refused_correction_leaves_the_first_member_of_every_listed_carrier_as_it_was(
    stage_url: str,
    get_json: Callable[..., Tuple[int, Any]],
    put_json: Callable[..., Tuple[int, Any]],
    bearer: Dict[str, str],
    members: str,
) -> None:
    firsts = _firsts(stage_url, get_json, bearer, members)
    refused = [put_json(url, CORRECTION[members], bearer)[0] for url, _ in firsts]
    assert (refused, [get_json(url, bearer)[1] for url, _ in firsts]) == (
        [403] * len(firsts), [one for _, one in firsts]
    )


@pytest.mark.parametrize("members", MEMBERS)
def test_the_workflows_key_removes_no_member_of_a_missing_carrier_through_the_deployed_api(
    stage_url: str, delete_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str],
    members: str,
) -> None:
    status, _ = delete_json(f"{stage_url}/carriers/0/{members}/0", bearer)
    assert status == 404


@pytest.mark.parametrize("members", MEMBERS)
def test_a_removal_from_a_carrier_that_is_not_there_names_the_carrier_through_the_deployed_api(
    stage_url: str, delete_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str],
    members: str,
) -> None:
    _, body = delete_json(f"{stage_url}/carriers/0/{members}/0", bearer)
    assert body["error"] == "No such carrier"


@pytest.mark.parametrize("members", MEMBERS)
def test_no_listed_carrier_loses_a_member_zero_through_the_deployed_api(
    stage_url: str,
    get_json: Callable[..., Tuple[int, Any]],
    delete_json: Callable[..., Tuple[int, Any]],
    bearer: Dict[str, str],
    members: str,
) -> None:
    _, listed = get_json(f"{stage_url}/carriers", bearer)
    removed = [
        delete_json(f"{stage_url}/carriers/{one['id']}/{members}/0", bearer) for one in listed
    ]
    assert removed == [(404, {"error": MISSING[members]})] * len(listed)


def test_the_fiber_segments_of_a_carrier_that_is_not_there_answer_404_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = get_json(f"{stage_url}/carriers/0/fiber-segments", bearer)
    assert status == 404


def test_the_fiber_segments_of_a_carrier_that_is_not_there_name_the_error_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = get_json(f"{stage_url}/carriers/0/fiber-segments", bearer)
    assert body["error"] == "No such carrier"


def test_every_listed_carrier_answers_a_list_of_fiber_segments_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, listed = get_json(f"{stage_url}/carriers", bearer)
    spans = [get_json(f"{stage_url}/carriers/{one['id']}/fiber-segments", bearer) for one in listed]
    assert [(status, type(fiber)) for status, fiber in spans] == [(200, list)] * len(listed)


def test_a_fiber_segment_without_ends_is_refused_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = post_json(f"{stage_url}/carriers/0/fiber-segments", {}, bearer)
    assert status == 400


def test_a_fiber_segment_without_ends_is_told_what_is_expected_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = post_json(f"{stage_url}/carriers/0/fiber-segments", {}, bearer)
    assert body["error"] == (
        'The body must be exactly '
        '{"a_municipality", "a_state", "z_municipality", "z_state", "submarine"}'
    )


def test_a_fiber_segment_for_a_carrier_that_is_not_there_answers_404_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = post_json(f"{stage_url}/carriers/0/fiber-segments", DEN_SLC, bearer)
    assert status == 404


def test_a_fiber_segment_for_a_carrier_that_is_not_there_names_the_error_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = post_json(f"{stage_url}/carriers/0/fiber-segments", DEN_SLC, bearer)
    assert body["error"] == "No such carrier"
