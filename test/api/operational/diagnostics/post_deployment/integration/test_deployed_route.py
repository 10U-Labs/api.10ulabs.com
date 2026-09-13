from typing import Any, Callable, Dict, Tuple

FUNCTION_NAME = "api-10ulabs-com-diagnostics"
PAYLOAD = {"message": "Hello 世界 🌍", "items": [{"id": i} for i in range(100)]}


def test_post_echo_answers_200_through_the_deployed_api(
    stage_url: str, post_json: Callable[[str, Any], Tuple[int, Dict[str, Any]]]
) -> None:
    status, _ = post_json(f"{stage_url}/diagnostics/echo", PAYLOAD)
    assert status == 200


def test_post_echo_returns_the_body_it_was_sent_through_the_deployed_api(
    stage_url: str, post_json: Callable[[str, Any], Tuple[int, Dict[str, Any]]]
) -> None:
    _, body = post_json(f"{stage_url}/diagnostics/echo", PAYLOAD)
    assert body["echo"] == PAYLOAD


def test_post_echo_names_the_request_through_the_deployed_api(
    stage_url: str, post_json: Callable[[str, Any], Tuple[int, Dict[str, Any]]]
) -> None:
    _, body = post_json(f"{stage_url}/diagnostics/echo", PAYLOAD)
    assert body["received_at"] != "N/A"


def test_diagnostics_function_runs_on_python_3_13(lambda_client: Any) -> None:
    function = lambda_client.get_function(FunctionName=FUNCTION_NAME)
    assert function["Configuration"]["Runtime"] == "python3.13"
