from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
CARRIER = "/carriers/{id}"


@pytest.fixture
def handler(endpoint: Callable[..., ModuleType]) -> ModuleType:
    return endpoint("carriers", "lambda/read_carrier")


def _get_one(carrier: str) -> Dict[str, Any]:
    return {"resource": CARRIER, "httpMethod": "GET", "pathParameters": {"id": carrier}}


def test_a_stored_carrier_answers_200(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_get_one("2"))["statusCode"] == 200


def test_a_stored_carrier_answers_by_id_and_name(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_get_one("2")) == {"id": 2, "name": "zayo"}


def test_a_carrier_is_read_from_the_table_the_environment_names(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_get_one("2"))
    assert store.gets[0]["TableName"] == "store"


def test_a_carrier_is_read_by_its_key_in_the_collection(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_get_one("2"))
    assert store.gets[0]["Key"] == {"PK": {"S": "carriers"}, "SK": {"S": "2"}}


def test_an_unknown_carrier_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_get_one("3"))["statusCode"] == 404


def test_an_unknown_carrier_names_the_error(served: Served) -> None:
    assert served(_get_one("3"))["error"] == "No such carrier"


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_an_id_that_is_not_a_number_answers_404(answer: Handler, carrier: str) -> None:
    assert answer(_get_one(carrier))["statusCode"] == 404


def test_the_counter_is_never_asked_for_as_a_carrier(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_get_one("#"))
    assert store.gets == []


def test_a_store_that_refuses_the_carrier_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_get_one("2"))["statusCode"] == 500


def test_a_store_that_refuses_the_carrier_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_one("2"))["error"] == "Failed to read the carrier"


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**_get_one("2"), "httpMethod": "PUT"})["statusCode"] == 404
