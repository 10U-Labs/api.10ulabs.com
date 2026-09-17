from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from fiber_segments import DEN_ORD, delete_fiber_segment
from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/remove_fiber_segment"


@pytest.fixture(name="span_removed")
def span_removed_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    return answer(delete_fiber_segment())


def test_a_stored_fiber_segment_is_removed_with_204(span_removed: Dict[str, Any]) -> None:
    assert span_removed["statusCode"] == 204


def test_a_span_removal_answers_no_content(span_removed: Dict[str, Any]) -> None:
    assert span_removed["body"] == ""


@pytest.mark.usefixtures("span_removed")
def test_a_removed_fiber_segment_is_no_longer_listed(
    fiber_segments_listed: Callable[[], Any]
) -> None:
    assert fiber_segments_listed() == [DEN_ORD]


@pytest.mark.usefixtures("span_removed")
def test_a_removed_fiber_segment_is_no_longer_served(
    fiber_segment_read: Callable[[], Dict[str, Any]]
) -> None:
    assert fiber_segment_read()["statusCode"] == 404


@pytest.mark.usefixtures("span_removed")
def test_a_span_removal_leaves_the_carrier_s_next_fiber_segment_where_it_was(
    lumen: Dict[str, Any]
) -> None:
    assert lumen["next_fiber_segment"] == {"N": "4"}


@pytest.mark.usefixtures("span_removed")
def test_a_span_removal_leaves_the_rest_of_the_carrier_as_it_was(store: SimpleNamespace) -> None:
    under = [item["SK"]["S"] for item in store.items if item["PK"] == {"S": "carriers/1"}]
    assert under == ["pops/3", "pops/1", "fiber-segments/1"]


@pytest.mark.usefixtures("span_removed")
def test_a_span_removal_goes_to_the_table_the_environment_names(store: SimpleNamespace) -> None:
    assert [one["TableName"] for one in store.deletes] == ["store"]


@pytest.mark.usefixtures("span_removed")
def test_a_span_removal_deletes_the_fiber_segment_under_the_carrier_by_its_id(
    store: SimpleNamespace
) -> None:
    assert [one["Key"] for one in store.deletes] == [
        {"PK": {"S": "carriers/1"}, "SK": {"S": "fiber-segments/3"}},
    ]


@pytest.mark.usefixtures("span_removed")
def test_a_span_removal_requires_the_fiber_segment_to_exist_in_the_store(
    store: SimpleNamespace
) -> None:
    assert store.deletes[0]["ConditionExpression"] == "attribute_exists(PK)"


@pytest.mark.usefixtures("span_removed")
def test_a_span_removal_reads_the_carrier_first(store: SimpleNamespace) -> None:
    assert [one["Key"] for one in store.gets] == [{"PK": {"S": "carriers"}, "SK": {"S": "1"}}]


def test_removing_a_fiber_segment_of_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(delete_fiber_segment("3"))["statusCode"] == 404


def test_removing_a_fiber_segment_of_an_unknown_carrier_names_the_carrier(
    served: Served
) -> None:
    assert served(delete_fiber_segment("3"))["error"] == "No such carrier"


def test_removing_a_fiber_segment_of_an_unknown_carrier_deletes_nothing(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(delete_fiber_segment("3"))
    assert store.deletes == []


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_removing_a_fiber_segment_of_an_id_that_is_not_a_number_answers_404(
    answer: Handler, carrier: str
) -> None:
    assert answer(delete_fiber_segment(carrier))["statusCode"] == 404


def test_removing_an_unknown_fiber_segment_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(delete_fiber_segment("1", "2"))["statusCode"] == 404


def test_removing_an_unknown_fiber_segment_names_the_fiber_segment(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(delete_fiber_segment("1", "2"))["error"] == "No such fiber segment"


def test_removing_an_unknown_fiber_segment_removes_nothing(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(delete_fiber_segment("1", "2"))
    assert len(store.items) == len(carriers)


@pytest.mark.parametrize("fiber_segment", ["#", "", "3/", "-1"])
def test_removing_a_fiber_segment_id_that_is_not_a_number_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], fiber_segment: str
) -> None:
    store.items.extend(carriers)
    assert answer(delete_fiber_segment("1", fiber_segment))["statusCode"] == 404


@pytest.mark.parametrize("fiber_segment", ["#", "", "3/", "-1"])
def test_removing_a_fiber_segment_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, fiber_segment: str
) -> None:
    answer(delete_fiber_segment("1", fiber_segment))
    assert (store.gets, store.deletes) == ([], [])


def test_a_store_that_refuses_the_span_removal_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(delete_fiber_segment())["statusCode"] == 500


def test_a_store_that_refuses_the_span_removal_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(delete_fiber_segment())["error"] == "Failed to delete the fiber segment"


@pytest.mark.usefixtures("span_removed")
def test_a_removed_fiber_segment_invalidates_the_carrier_s_fiber_segments_and_its_own_url(
    distribution: SimpleNamespace
) -> None:
    assert distribution.invalidated == [
        ["/carriers/1/fiber-segments", "/carriers/1/fiber-segments/3"]
    ]


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**delete_fiber_segment(), "httpMethod": "PUT"})["statusCode"] == 404


def test_another_resource_answers_404(answer: Handler) -> None:
    event = {**delete_fiber_segment(), "resource": "/carriers/{id}/fiber-segments"}
    assert answer(event)["statusCode"] == 404
