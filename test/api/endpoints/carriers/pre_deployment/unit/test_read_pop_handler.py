from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler
from pops import CHICAGO, get_pop

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/read_pop"


def test_a_stored_pop_answers_200(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(get_pop())["statusCode"] == 200


def test_a_stored_pop_answers_by_its_id_and_where_it_is(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(get_pop()) == CHICAGO


@pytest.fixture(name="pop_gets")
def pop_gets_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    store.items.extend(carriers)
    answer(get_pop())
    return [dict(one) for one in store.gets]


def test_a_pop_is_read_after_its_carrier(pop_gets: List[Dict[str, Any]]) -> None:
    assert [one["Key"] for one in pop_gets] == [
        {"PK": {"S": "carriers"}, "SK": {"S": "1"}},
        {"PK": {"S": "carriers/1"}, "SK": {"S": "pops/3"}},
    ]


def test_a_pop_is_read_from_the_table_the_environment_names(
    pop_gets: List[Dict[str, Any]]
) -> None:
    assert [one["TableName"] for one in pop_gets] == ["store", "store"]


def test_a_pop_of_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(get_pop("3"))["statusCode"] == 404


def test_a_pop_of_an_unknown_carrier_names_the_carrier(served: Served) -> None:
    assert served(get_pop("3"))["error"] == "No such carrier"


def test_a_pop_of_an_unknown_carrier_is_not_looked_for(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(get_pop("3"))
    assert len(store.gets) == 1


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_a_pop_of_an_id_that_is_not_a_number_answers_404(answer: Handler, carrier: str) -> None:
    assert answer(get_pop(carrier))["statusCode"] == 404


def test_an_unknown_pop_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(get_pop("1", "2"))["statusCode"] == 404


def test_an_unknown_pop_names_the_pop(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(get_pop("1", "2"))["error"] == "No such pop"


@pytest.mark.parametrize("pop", ["#", "", "3/", "-1"])
def test_a_pop_id_that_is_not_a_number_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], pop: str
) -> None:
    store.items.extend(carriers)
    assert answer(get_pop("1", pop))["statusCode"] == 404


@pytest.mark.parametrize("pop", ["#", "", "3/", "-1"])
def test_a_pop_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, pop: str
) -> None:
    answer(get_pop("1", pop))
    assert store.gets == []


def test_a_store_that_refuses_the_pop_read_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(get_pop())["statusCode"] == 500


def test_a_store_that_refuses_the_pop_read_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(get_pop())["error"] == "Failed to read the pop"


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**get_pop(), "httpMethod": "DELETE"})["statusCode"] == 404


def test_another_resource_answers_404(answer: Handler) -> None:
    assert answer({**get_pop(), "resource": "/carriers/{id}/pops"})["statusCode"] == 404
