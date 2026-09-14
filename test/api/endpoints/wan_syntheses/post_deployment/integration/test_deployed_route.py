from typing import Any, Callable, Dict, List, Tuple

SYNTHESES = "/wan-syntheses"


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


def test_the_wan_pops_of_a_synthesis_that_is_not_there_answer_404_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = get_json(f"{stage_url}{SYNTHESES}/0/wan-pops", bearer)
    assert status == 404


def test_the_wan_pops_of_a_synthesis_that_is_not_there_name_the_synthesis_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = get_json(f"{stage_url}{SYNTHESES}/0/wan-pops", bearer)
    assert body["error"] == "No such wan synthesis"


def _succeeded(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> List[int]:
    _, listed = get_json(f"{stage_url}{SYNTHESES}", bearer)
    records = [get_json(f"{stage_url}{SYNTHESES}/{one['id']}", bearer)[1] for one in listed]
    return [record["id"] for record in records if record["status"] == "success"]


def test_every_succeeded_synthesis_answers_a_list_of_wan_pops_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    succeeded = _succeeded(stage_url, get_json, bearer)
    answered = [get_json(f"{stage_url}{SYNTHESES}/{one}/wan-pops", bearer) for one in succeeded]
    assert [(status, type(pops)) for status, pops in answered] == [(200, list)] * len(succeeded)


def test_a_wan_pop_of_a_synthesis_that_is_not_there_answers_404_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    status, _ = get_json(f"{stage_url}{SYNTHESES}/0/wan-pops/0", bearer)
    assert status == 404


def test_a_wan_pop_of_a_synthesis_that_is_not_there_names_the_synthesis_through_the_deployed_api(
    stage_url: str, get_json: Callable[..., Tuple[int, Any]], bearer: Dict[str, str]
) -> None:
    _, body = get_json(f"{stage_url}{SYNTHESES}/0/wan-pops/0", bearer)
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
