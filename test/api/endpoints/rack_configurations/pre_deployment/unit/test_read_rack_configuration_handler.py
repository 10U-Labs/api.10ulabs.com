from typing import Any, Callable, Dict

import pytest

from lambda_http import Handler
from rack_events import RACK_CONFIGURATION, UNKNOWN, get

Served = Callable[[Dict[str, Any]], Any]
Stored = Callable[[Dict[str, Any]], str]
HANDLER = "lambda/read_rack_configuration"


def test_a_stored_configuration_is_read_back(
    served: Served, stored: Stored, configuration: Dict[str, Any]
) -> None:
    assert served(get(stored(configuration)))["configuration"] == configuration


def test_a_read_answers_200(answer: Handler, stored: Stored, configuration: Dict[str, Any]) -> None:
    assert answer(get(stored(configuration)))["statusCode"] == 200


def test_a_read_names_the_hash(
    served: Served, stored: Stored, configuration: Dict[str, Any]
) -> None:
    config_hash = stored(configuration)
    assert served(get(config_hash))["config_hash"] == config_hash


def test_a_read_allows_any_origin(
    answer: Handler, stored: Stored, configuration: Dict[str, Any]
) -> None:
    headers = answer(get(stored(configuration)))["headers"]
    assert headers["Access-Control-Allow-Origin"] == "*"


def test_an_unknown_hash_answers_404(answer: Handler) -> None:
    assert answer(get(UNKNOWN))["statusCode"] == 404


def test_an_unknown_hash_says_so(served: Served) -> None:
    assert served(get(UNKNOWN))["error"] == "Configuration not found"


def test_an_unknown_hash_is_refused_to_any_origin(answer: Handler) -> None:
    assert answer(get(UNKNOWN))["headers"]["Access-Control-Allow-Origin"] == "*"


@pytest.mark.parametrize("config_hash", ["", "short", "lowercase", "TOOLONGHASH", "ABCDEFGH!"])
def test_a_malformed_hash_answers_400(answer: Handler, config_hash: str) -> None:
    assert answer(get(config_hash))["statusCode"] == 400


def test_a_read_without_a_hash_answers_400(answer: Handler) -> None:
    event = {**get("ABCDEFGHI"), "pathParameters": None}
    assert answer(event)["statusCode"] == 400


def test_a_put_on_a_member_answers_404(answer: Handler) -> None:
    event = {"resource": RACK_CONFIGURATION, "httpMethod": "PUT", "pathParameters": {"id": UNKNOWN}}
    assert answer(event)["statusCode"] == 404
