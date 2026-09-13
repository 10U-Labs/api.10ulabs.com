import json
from types import ModuleType
from typing import Any, Dict

GET_HEALTH = {"path": "/health", "httpMethod": "GET"}


def _answer(health_handler: ModuleType, event: Dict[str, Any]) -> Dict[str, Any]:
    return dict(health_handler.lambda_handler(event, None))


def _body(health_handler: ModuleType, event: Dict[str, Any]) -> Dict[str, Any]:
    return dict(json.loads(_answer(health_handler, event)["body"]))


def test_get_health_answers_200(health_handler: ModuleType) -> None:
    assert _answer(health_handler, GET_HEALTH)["statusCode"] == 200


def test_get_health_answers_json(health_handler: ModuleType) -> None:
    assert _answer(health_handler, GET_HEALTH)["headers"]["Content-Type"] == "application/json"


def test_get_health_says_healthy(health_handler: ModuleType) -> None:
    assert _body(health_handler, GET_HEALTH)["status"] == "healthy"


def test_get_health_names_the_service(health_handler: ModuleType) -> None:
    assert _body(health_handler, GET_HEALTH)["service"] == "10U Labs API"


def test_get_health_carries_a_three_part_version(health_handler: ModuleType) -> None:
    assert len(_body(health_handler, GET_HEALTH)["version"].split(".")) == 3


def test_another_path_answers_404(health_handler: ModuleType) -> None:
    assert _answer(health_handler, {"path": "/unknown", "httpMethod": "GET"})["statusCode"] == 404


def test_another_method_answers_404(health_handler: ModuleType) -> None:
    assert _answer(health_handler, {"path": "/health", "httpMethod": "POST"})["statusCode"] == 404


def test_a_refusal_names_the_error(health_handler: ModuleType) -> None:
    assert _body(health_handler, {"path": "/unknown", "httpMethod": "GET"})["error"] == "Not found"
