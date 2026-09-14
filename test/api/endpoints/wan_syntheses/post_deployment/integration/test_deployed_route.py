from typing import Any, Callable, Dict, Tuple

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
