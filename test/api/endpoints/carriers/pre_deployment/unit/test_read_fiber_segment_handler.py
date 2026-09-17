from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from fiber_segments import NYC_AMS, get_fiber_segment
from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/read_fiber_segment"


def test_a_stored_fiber_segment_answers_200(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(get_fiber_segment())["statusCode"] == 200


def test_a_stored_fiber_segment_answers_by_its_id_and_the_span_it_covers(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(get_fiber_segment()) == NYC_AMS


@pytest.fixture(name="fiber_segment_gets")
def fiber_segment_gets_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    store.items.extend(carriers)
    answer(get_fiber_segment())
    return [dict(one) for one in store.gets]


def test_a_fiber_segment_is_read_after_its_carrier(
    fiber_segment_gets: List[Dict[str, Any]]
) -> None:
    assert [one["Key"] for one in fiber_segment_gets] == [
        {"PK": {"S": "carriers"}, "SK": {"S": "1"}},
        {"PK": {"S": "carriers/1"}, "SK": {"S": "fiber-segments/3"}},
    ]


def test_a_fiber_segment_is_read_from_the_table_the_environment_names(
    fiber_segment_gets: List[Dict[str, Any]]
) -> None:
    assert [one["TableName"] for one in fiber_segment_gets] == ["store", "store"]


def test_a_fiber_segment_of_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(get_fiber_segment("3"))["statusCode"] == 404


def test_a_fiber_segment_of_an_unknown_carrier_names_the_carrier(served: Served) -> None:
    assert served(get_fiber_segment("3"))["error"] == "No such carrier"


def test_a_fiber_segment_of_an_unknown_carrier_is_not_looked_for(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(get_fiber_segment("3"))
    assert len(store.gets) == 1


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_a_fiber_segment_of_an_id_that_is_not_a_number_answers_404(
    answer: Handler, carrier: str
) -> None:
    assert answer(get_fiber_segment(carrier))["statusCode"] == 404


def test_an_unknown_fiber_segment_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(get_fiber_segment("1", "2"))["statusCode"] == 404


def test_an_unknown_fiber_segment_names_the_fiber_segment(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(get_fiber_segment("1", "2"))["error"] == "No such fiber segment"


@pytest.mark.parametrize("fiber_segment", ["#", "", "3/", "-1"])
def test_a_fiber_segment_id_that_is_not_a_number_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], fiber_segment: str
) -> None:
    store.items.extend(carriers)
    assert answer(get_fiber_segment("1", fiber_segment))["statusCode"] == 404


@pytest.mark.parametrize("fiber_segment", ["#", "", "3/", "-1"])
def test_a_fiber_segment_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, fiber_segment: str
) -> None:
    answer(get_fiber_segment("1", fiber_segment))
    assert store.gets == []


def test_a_store_that_refuses_the_fiber_segment_read_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(get_fiber_segment())["statusCode"] == 500


def test_a_store_that_refuses_the_fiber_segment_read_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(get_fiber_segment())["error"] == "Failed to read the fiber segment"


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**get_fiber_segment(), "httpMethod": "DELETE"})["statusCode"] == 404


def test_another_resource_answers_404(answer: Handler) -> None:
    event = {**get_fiber_segment(), "resource": "/carriers/{id}/fiber-segments"}
    assert answer(event)["statusCode"] == 404
