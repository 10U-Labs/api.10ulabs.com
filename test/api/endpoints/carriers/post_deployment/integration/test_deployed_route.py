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
