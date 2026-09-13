import json
from types import ModuleType, SimpleNamespace
from typing import Any, Dict

import pytest

RACK_CONFIGURATIONS = "/v1/rack-configurations"


def _post(body: Any) -> Dict[str, Any]:
    raw = body if isinstance(body, str) else json.dumps(body)
    return {"resource": RACK_CONFIGURATIONS, "httpMethod": "POST", "body": raw}


def _submission(configuration: Any, **extra: Any) -> Dict[str, Any]:
    return {"device_id": "device-1", "configuration": configuration, **extra}


def _answer(rack_handler: ModuleType, event: Dict[str, Any]) -> Dict[str, Any]:
    return dict(rack_handler.lambda_handler(event, None))


def _body(rack_handler: ModuleType, event: Dict[str, Any]) -> Dict[str, Any]:
    return dict(json.loads(_answer(rack_handler, event)["body"]))


def test_a_valid_configuration_is_stored(
    rack_handler: ModuleType, configuration: Dict[str, Any], table: SimpleNamespace
) -> None:
    _answer(rack_handler, _post(_submission(configuration)))
    assert json.loads(table.items[0]["configuration"]["S"]) == configuration


def test_a_stored_configuration_answers_200(
    rack_handler: ModuleType, configuration: Dict[str, Any]
) -> None:
    assert _answer(rack_handler, _post(_submission(configuration)))["statusCode"] == 200


def test_the_answer_carries_a_nine_character_hash(
    rack_handler: ModuleType, configuration: Dict[str, Any]
) -> None:
    config_hash = _body(rack_handler, _post(_submission(configuration)))["config_hash"]
    assert len(config_hash) == 9


def test_the_hash_is_the_one_10ulabs_com_computes(rack_handler: ModuleType) -> None:
    smallest = {"rackHeight": 1, "rackCount": 1, "placedParts": []}
    assert rack_handler.configuration_hash(smallest) == "YGMVKYYYT"


def test_the_hash_is_stored_with_the_configuration(
    rack_handler: ModuleType, configuration: Dict[str, Any], table: SimpleNamespace
) -> None:
    config_hash = _body(rack_handler, _post(_submission(configuration)))["config_hash"]
    assert table.items[0]["config_hash"]["S"] == config_hash


def test_the_device_is_stored_with_the_configuration(
    rack_handler: ModuleType, configuration: Dict[str, Any], table: SimpleNamespace
) -> None:
    _answer(rack_handler, _post(_submission(configuration)))
    assert table.items[0]["device_id"]["S"] == "device-1"


def test_the_same_configuration_answers_the_same_hash_again(
    rack_handler: ModuleType, configuration: Dict[str, Any]
) -> None:
    first = _body(rack_handler, _post(_submission(configuration)))["config_hash"]
    assert _body(rack_handler, _post(_submission(configuration)))["config_hash"] == first


def test_the_same_configuration_is_stored_once(
    rack_handler: ModuleType, configuration: Dict[str, Any], table: SimpleNamespace
) -> None:
    _answer(rack_handler, _post(_submission(configuration)))
    _answer(rack_handler, _post(_submission(configuration)))
    assert len(table.items) == 1


def test_a_missing_device_is_refused(
    rack_handler: ModuleType, configuration: Dict[str, Any]
) -> None:
    body = _body(rack_handler, _post({"configuration": configuration}))
    assert body["error"] == "Missing required field: device_id"


def test_a_missing_configuration_is_refused(rack_handler: ModuleType) -> None:
    body = _body(rack_handler, _post({"device_id": "device-1"}))
    assert body["error"] == "Missing required field: configuration"


@pytest.mark.parametrize("field", ["rackHeight", "rackCount", "placedParts"])
def test_a_missing_configuration_field_is_named(
    rack_handler: ModuleType, configuration: Dict[str, Any], field: str
) -> None:
    del configuration[field]
    body = _body(rack_handler, _post(_submission(configuration)))
    assert body["error"] == f"Missing required field: {field}"


@pytest.mark.parametrize("field, value, error", [
    ("rackHeight", "42", "rackHeight must be an integer"),
    ("rackCount", 1.5, "rackCount must be an integer"),
    ("placedParts", {}, "placedParts must be an array"),
    ("rackHeight", 43, "rackHeight must be between 1 and 42"),
    ("rackHeight", 0, "rackHeight must be between 1 and 42"),
    ("rackCount", 0, "rackCount must be at least 1"),
])
def test_an_invalid_configuration_field_is_refused(
    rack_handler: ModuleType, configuration: Dict[str, Any], field: str, value: Any, error: str
) -> None:
    body = _body(rack_handler, _post(_submission({**configuration, field: value})))
    assert body["error"] == error


def test_a_refusal_answers_400(rack_handler: ModuleType, configuration: Dict[str, Any]) -> None:
    event = _post(_submission({**configuration, "rackCount": 0}))
    assert _answer(rack_handler, event)["statusCode"] == 400


def test_a_body_that_is_not_json_is_refused(rack_handler: ModuleType) -> None:
    assert _body(rack_handler, _post("not json"))["error"] == "Invalid JSON"


def test_a_table_that_refuses_the_write_answers_500(
    rack_handler: ModuleType, configuration: Dict[str, Any], table: SimpleNamespace
) -> None:
    table.failing = True
    assert _answer(rack_handler, _post(_submission(configuration)))["statusCode"] == 500


def test_every_answer_allows_any_origin(rack_handler: ModuleType) -> None:
    response = _answer(rack_handler, {"resource": "/other", "httpMethod": "GET"})
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"


def test_another_resource_answers_404(rack_handler: ModuleType) -> None:
    response = _answer(rack_handler, {"resource": "/other", "httpMethod": "GET"})
    assert response["statusCode"] == 404
