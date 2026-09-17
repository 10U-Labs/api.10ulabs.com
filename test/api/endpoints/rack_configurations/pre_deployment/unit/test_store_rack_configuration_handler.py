import json
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict

import pytest

from lambda_http import Handler
from rack_events import RACK_CONFIGURATIONS, post, submission

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/store_rack_configuration"


def test_a_valid_configuration_is_stored(
    answer: Handler, configuration: Dict[str, Any], table: SimpleNamespace
) -> None:
    answer(post(submission(configuration)))
    assert json.loads(table.items[0]["configuration"]["S"]) == configuration


def test_a_stored_configuration_answers_200(
    answer: Handler, configuration: Dict[str, Any]
) -> None:
    assert answer(post(submission(configuration)))["statusCode"] == 200


def test_the_answer_carries_a_nine_character_hash(
    served: Served, configuration: Dict[str, Any]
) -> None:
    assert len(served(post(submission(configuration)))["config_hash"]) == 9


def test_the_hash_is_the_one_10ulabs_com_computes(handler: ModuleType) -> None:
    smallest = {"rackHeight": 1, "rackCount": 1, "placedParts": []}
    assert handler.configuration_hash(smallest) == "YGMVKYYYT"


def test_the_hash_is_stored_with_the_configuration(
    served: Served, configuration: Dict[str, Any], table: SimpleNamespace
) -> None:
    config_hash = served(post(submission(configuration)))["config_hash"]
    assert table.items[0]["config_hash"]["S"] == config_hash


def test_the_device_is_stored_with_the_configuration(
    answer: Handler, configuration: Dict[str, Any], table: SimpleNamespace
) -> None:
    answer(post(submission(configuration)))
    assert table.items[0]["device_id"]["S"] == "device-1"


def test_the_same_configuration_answers_the_same_hash_again(
    served: Served, configuration: Dict[str, Any]
) -> None:
    first = served(post(submission(configuration)))["config_hash"]
    assert served(post(submission(configuration)))["config_hash"] == first


def test_the_same_configuration_is_stored_once(
    answer: Handler, configuration: Dict[str, Any], table: SimpleNamespace
) -> None:
    answer(post(submission(configuration)))
    answer(post(submission(configuration)))
    assert len(table.items) == 1


def test_a_first_store_invalidates_the_hash_it_answers(
    served: Served, configuration: Dict[str, Any], distribution: SimpleNamespace
) -> None:
    config_hash = served(post(submission(configuration)))["config_hash"]
    assert distribution.invalidated == [[f"{RACK_CONFIGURATIONS}/{config_hash}"]]


def test_a_repeat_store_invalidates_nothing(
    answer: Handler, configuration: Dict[str, Any], distribution: SimpleNamespace
) -> None:
    answer(post(submission(configuration)))
    answer(post(submission(configuration)))
    assert len(distribution.invalidated) == 1


def test_a_refused_store_invalidates_nothing(
    answer: Handler,
    configuration: Dict[str, Any],
    table: SimpleNamespace,
    distribution: SimpleNamespace,
) -> None:
    table.failing = True
    answer(post(submission(configuration)))
    assert distribution.invalidated == []


def test_a_missing_device_is_refused(served: Served, configuration: Dict[str, Any]) -> None:
    body = served(post({"configuration": configuration}))
    assert body["error"] == "Missing required field: device_id"


def test_a_missing_configuration_is_refused(served: Served) -> None:
    body = served(post({"device_id": "device-1"}))
    assert body["error"] == "Missing required field: configuration"


@pytest.mark.parametrize("field", ["rackHeight", "rackCount", "placedParts"])
def test_a_missing_configuration_field_is_named(
    served: Served, configuration: Dict[str, Any], field: str
) -> None:
    del configuration[field]
    body = served(post(submission(configuration)))
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
    served: Served, configuration: Dict[str, Any], field: str, value: Any, error: str
) -> None:
    body = served(post(submission({**configuration, field: value})))
    assert body["error"] == error


def test_a_refusal_answers_400(answer: Handler, configuration: Dict[str, Any]) -> None:
    event = post(submission({**configuration, "rackCount": 0}))
    assert answer(event)["statusCode"] == 400


def test_a_body_that_is_not_json_is_refused(served: Served) -> None:
    assert served(post("not json"))["error"] == "Invalid JSON"


def test_a_table_that_refuses_the_write_answers_500(
    answer: Handler, configuration: Dict[str, Any], table: SimpleNamespace
) -> None:
    table.failing = True
    assert answer(post(submission(configuration)))["statusCode"] == 500


def test_a_refusal_allows_any_origin(answer: Handler) -> None:
    response = answer(post("not json"))
    assert (response["statusCode"], response["headers"]["Access-Control-Allow-Origin"]) == (
        400, "*"
    )


def test_a_get_on_the_collection_answers_404(answer: Handler) -> None:
    response = answer({"resource": RACK_CONFIGURATIONS, "httpMethod": "GET"})
    assert (response["statusCode"], response["headers"]["Access-Control-Allow-Origin"]) == (
        404, "*"
    )
