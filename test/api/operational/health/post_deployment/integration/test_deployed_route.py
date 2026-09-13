from typing import Any, Callable, Dict, Tuple

FUNCTION_NAME = "api-10ulabs-com-health"


def test_get_health_answers_200_through_the_deployed_api(
    stage_url: str, get_json: Callable[[str], Tuple[int, Dict[str, Any]]]
) -> None:
    status, _ = get_json(f"{stage_url}/health")
    assert status == 200


def test_get_health_says_healthy_through_the_deployed_api(
    stage_url: str, get_json: Callable[[str], Tuple[int, Dict[str, Any]]]
) -> None:
    _, body = get_json(f"{stage_url}/health")
    assert body["status"] == "healthy"


def test_health_function_runs_on_python_3_13(lambda_client: Any) -> None:
    function = lambda_client.get_function(FunctionName=FUNCTION_NAME)
    assert function["Configuration"]["Runtime"] == "python3.13"


def test_health_function_calls_aws_over_fips_endpoints(lambda_client: Any) -> None:
    function = lambda_client.get_function(FunctionName=FUNCTION_NAME)
    assert function["Configuration"]["Environment"]["Variables"]["AWS_USE_FIPS_ENDPOINT"] == "true"
