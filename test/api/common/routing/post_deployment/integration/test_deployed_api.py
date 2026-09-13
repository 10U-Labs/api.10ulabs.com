from typing import Any, Callable, Dict, Tuple


def test_rest_api_is_regional(apigateway_client: Any, api_id: str) -> None:
    api = apigateway_client.get_rest_api(restApiId=api_id)
    assert api["endpointConfiguration"]["types"] == ["REGIONAL"]


def test_prod_stage_is_deployed(apigateway_client: Any, api_id: str) -> None:
    stage = apigateway_client.get_stage(restApiId=api_id, stageName="prod")
    assert stage["deploymentId"]


def test_an_undefined_route_answers_404(
    stage_url: str, get_json: Callable[[str], Tuple[int, Dict[str, Any]]]
) -> None:
    status, _ = get_json(f"{stage_url}/nothing/here")
    assert status == 404


def test_an_undefined_route_names_the_path_it_refused(
    stage_url: str, get_json: Callable[[str], Tuple[int, Dict[str, Any]]]
) -> None:
    _, body = get_json(f"{stage_url}/nothing/here")
    assert body["path"] == "/nothing/here"
