from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler
from pops import CHICAGO, DENVER, get_pops

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/list_pops"


def test_the_pops_of_a_stored_carrier_answer_200(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(get_pops())["statusCode"] == 200


def test_the_pops_answer_as_rows_in_id_order(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(get_pops()) == [DENVER, CHICAGO]


def test_a_carrier_without_pops_answers_none(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(get_pops("2")) == []


@pytest.fixture(name="pops_query")
def pops_query_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(get_pops())
    return dict(store.queries[-1])


def test_the_pops_are_read_from_under_the_carrier(pops_query: Dict[str, Any]) -> None:
    assert pops_query["ExpressionAttributeValues"] == {
        ":pk": {"S": "carriers/1"}, ":prefix": {"S": "pops/"},
    }


def test_the_pops_are_read_from_the_table_the_environment_names(
    pops_query: Dict[str, Any]
) -> None:
    assert pops_query["TableName"] == "store"


def test_the_pops_of_an_unknown_carrier_answer_404(answer: Handler) -> None:
    assert answer(get_pops("3"))["statusCode"] == 404


def test_the_pops_of_an_unknown_carrier_name_the_error(served: Served) -> None:
    assert served(get_pops("3"))["error"] == "No such carrier"


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_the_pops_of_an_id_that_is_not_a_number_answer_404(answer: Handler, carrier: str) -> None:
    assert answer(get_pops(carrier))["statusCode"] == 404


def test_a_store_that_refuses_the_pops_answers_500(answer: Handler, store: SimpleNamespace) -> None:
    store.failing = True
    assert answer(get_pops())["statusCode"] == 500


def test_a_store_that_refuses_the_pops_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(get_pops())["error"] == "Failed to read the pops"


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**get_pops(), "httpMethod": "POST"})["statusCode"] == 404


def test_another_resource_answers_404(answer: Handler) -> None:
    assert answer({**get_pops(), "resource": "/carriers/{id}"})["statusCode"] == 404
