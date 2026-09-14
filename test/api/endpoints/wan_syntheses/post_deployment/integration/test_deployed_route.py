from typing import Any, Callable, Dict, List, Tuple

import pytest

SYNTHESES = "/wan-syntheses"
WAN_PARTS = ["wan-pops", "backbone-circuits", "homing-circuits", "fiber-segments"]
SERVED_INPUTS = ["sites", "hyperscale-cloud-service-provider-regions"]
INPUTS = SERVED_INPUTS + [
    "off-net", "forced-wan-pops", "forced-circuits", "forced-homes", "prohibited-wan-pops",
    "prohibited-circuits", "degree-exempt-wan-pops",
]
PARTS = WAN_PARTS + INPUTS
MEMBERS = ["wan-pops"] + SERVED_INPUTS


def test_the_syntheses_are_listed_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = get_json(f"{stage_url}{SYNTHESES}", bearer)
    assert status == 200


def test_the_deployed_api_answers_a_list_of_syntheses(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = get_json(f"{stage_url}{SYNTHESES}", bearer)
    assert isinstance(body, list)


def test_the_syntheses_refuse_a_call_without_a_token_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]]
) -> None:
    status, _ = get_json(f"{stage_url}{SYNTHESES}")
    assert status == 401


def test_a_synthesis_that_is_not_there_answers_404_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = get_json(f"{stage_url}{SYNTHESES}/0", bearer)
    assert status == 404


def test_a_synthesis_that_is_not_there_names_the_error_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = get_json(f"{stage_url}{SYNTHESES}/0", bearer)
    assert body["error"] == "No such wan synthesis"


def test_every_listed_synthesis_is_served_at_its_own_url_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, listed = get_json(f"{stage_url}{SYNTHESES}", bearer)
    served = [get_json(f"{stage_url}{SYNTHESES}/{one['id']}", bearer) for one in listed]
    assert [(status, record["id"], record["label"]) for status, record in served] == [
        (200, one["id"], one["label"]) for one in listed
    ]


@pytest.mark.parametrize("part", PARTS)
def test_a_part_of_a_synthesis_that_is_not_there_answers_404_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str], part: str
) -> None:
    status, _ = get_json(f"{stage_url}{SYNTHESES}/0/{part}", bearer)
    assert status == 404


@pytest.mark.parametrize("part", PARTS)
def test_a_part_of_a_synthesis_that_is_not_there_names_the_synthesis_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str], part: str
) -> None:
    _, body = get_json(f"{stage_url}{SYNTHESES}/0/{part}", bearer)
    assert body["error"] == "No such wan synthesis"


def _succeeded(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> List[int]:
    _, listed = get_json(f"{stage_url}{SYNTHESES}", bearer)
    records = [get_json(f"{stage_url}{SYNTHESES}/{one['id']}", bearer)[1] for one in listed]
    return [record["id"] for record in records if record["status"] == "success"]


@pytest.mark.parametrize("part", WAN_PARTS)
def test_every_succeeded_synthesis_answers_a_list_for_each_part_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str], part: str
) -> None:
    succeeded = _succeeded(stage_url, get_json, bearer)
    answered = [get_json(f"{stage_url}{SYNTHESES}/{one}/{part}", bearer) for one in succeeded]
    assert [(status, type(rows)) for status, rows in answered] == [(200, list)] * len(succeeded)


@pytest.mark.parametrize("part", MEMBERS)
def test_a_member_of_a_synthesis_that_is_not_there_answers_404_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str], part: str
) -> None:
    status, _ = get_json(f"{stage_url}{SYNTHESES}/0/{part}/0", bearer)
    assert status == 404


@pytest.mark.parametrize("part", MEMBERS)
def test_a_member_of_a_synthesis_that_is_not_there_names_the_synthesis_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str], part: str
) -> None:
    _, body = get_json(f"{stage_url}{SYNTHESES}/0/{part}/0", bearer)
    assert body["error"] == "No such wan synthesis"


def test_the_first_wan_pop_of_every_succeeded_synthesis_is_served_at_its_own_url(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    firsts = [
        (f"{stage_url}{SYNTHESES}/{one}/wan-pops/{pop['id']}", pop)
        for one in _succeeded(stage_url, get_json, bearer)
        for pop in get_json(f"{stage_url}{SYNTHESES}/{one}/wan-pops", bearer)[1][:1]
    ]
    assert [get_json(url, bearer) for url, _ in firsts] == [(200, pop) for _, pop in firsts]


@pytest.mark.parametrize("part", INPUTS)
def test_every_listed_synthesis_answers_a_list_for_each_input_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str], part: str
) -> None:
    _, listed = get_json(f"{stage_url}{SYNTHESES}", bearer)
    answered = [get_json(f"{stage_url}{SYNTHESES}/{one['id']}/{part}", bearer) for one in listed]
    assert [(status, type(rows)) for status, rows in answered] == [(200, list)] * len(listed)


@pytest.mark.parametrize("part", SERVED_INPUTS)
def test_the_first_input_of_every_listed_synthesis_is_served_at_its_own_url(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str], part: str
) -> None:
    _, listed = get_json(f"{stage_url}{SYNTHESES}", bearer)
    firsts = [
        (f"{stage_url}{SYNTHESES}/{one['id']}/{part}/{given['id']}", given)
        for one in listed
        for given in get_json(f"{stage_url}{SYNTHESES}/{one['id']}/{part}", bearer)[1][:1]
    ]
    assert [get_json(url, bearer) for url, _ in firsts] == [(200, one) for _, one in firsts]


def test_a_creation_refuses_a_call_without_a_token_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Any]]
) -> None:
    status, _ = post_json(f"{stage_url}{SYNTHESES}", {})
    assert status == 401


def test_the_workflows_key_is_admitted_to_create_a_synthesis_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = post_json(f"{stage_url}{SYNTHESES}", {}, bearer)
    assert status == 400


def test_a_body_without_the_run_s_inputs_names_every_field_through_the_deployed_api(
    stage_url: str, post_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = post_json(f"{stage_url}{SYNTHESES}", {"label": "minuteman"}, bearer)
    assert body["error"].startswith("The body must be exactly the run's label, wan_pop_count")
