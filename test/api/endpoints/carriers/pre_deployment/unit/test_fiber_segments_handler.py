from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
FIBER_SEGMENTS = "/carriers/{carrier}/fiber-segments"
DEN_ORD = {"id": 1, "a_municipality": "Denver", "a_state": "CO",
           "z_municipality": "Chicago", "z_state": "IL", "submarine": False}
NYC_AMS = {"id": 3, "a_municipality": "New York", "a_state": "NY",
           "z_municipality": "Amsterdam", "z_state": "", "submarine": True}


def _get_fiber_segments(carrier: str = "1") -> Dict[str, Any]:
    event = {"resource": FIBER_SEGMENTS, "httpMethod": "GET"}
    return {**event, "pathParameters": {"carrier": carrier}}


def test_the_fiber_segments_of_a_stored_carrier_answer_200(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_get_fiber_segments())["statusCode"] == 200


def test_the_fiber_segments_answer_as_spans_in_id_order(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_get_fiber_segments()) == [DEN_ORD, NYC_AMS]


def test_a_carrier_without_fiber_segments_answers_none(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_get_fiber_segments("2")) == []


@pytest.fixture(name="fiber_segments_query")
def fiber_segments_query_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(_get_fiber_segments())
    return dict(store.queries[-1])


def test_the_fiber_segments_are_read_from_under_the_carrier(
    fiber_segments_query: Dict[str, Any]
) -> None:
    assert fiber_segments_query["ExpressionAttributeValues"] == {
        ":pk": {"S": "carriers/1"}, ":prefix": {"S": "fiber-segments/"},
    }


def test_the_fiber_segments_are_read_from_the_table_the_environment_names(
    fiber_segments_query: Dict[str, Any]
) -> None:
    assert fiber_segments_query["TableName"] == "store"


def test_the_fiber_segments_are_read_after_the_carrier(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_get_fiber_segments())
    assert [one["Key"] for one in store.gets] == [{"PK": {"S": "carriers"}, "SK": {"S": "1"}}]


def test_the_fiber_segments_of_an_unknown_carrier_answer_404(answer: Handler) -> None:
    assert answer(_get_fiber_segments("3"))["statusCode"] == 404


def test_the_fiber_segments_of_an_unknown_carrier_name_the_error(served: Served) -> None:
    assert served(_get_fiber_segments("3"))["error"] == "No such carrier"


def test_the_fiber_segments_of_an_unknown_carrier_are_not_looked_for(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_get_fiber_segments("3"))
    assert store.queries == []


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_the_fiber_segments_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, carrier: str
) -> None:
    assert answer(_get_fiber_segments(carrier))["statusCode"] == 404


def test_a_store_that_refuses_the_fiber_segments_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_get_fiber_segments())["statusCode"] == 500


def test_a_store_that_refuses_the_fiber_segments_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_fiber_segments())["error"] == "Failed to read the fiber segments"
