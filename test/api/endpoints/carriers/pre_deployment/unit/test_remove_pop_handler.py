from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler
from pops import DENVER, delete_pop

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/remove_pop"


@pytest.fixture(name="removed")
def removed_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    return answer(delete_pop())


def test_a_stored_pop_is_removed_with_204(removed: Dict[str, Any]) -> None:
    assert removed["statusCode"] == 204


def test_a_removal_answers_no_content(removed: Dict[str, Any]) -> None:
    assert removed["body"] == ""


@pytest.mark.usefixtures("removed")
def test_a_removed_pop_is_no_longer_listed(pops_listed: Callable[[], Any]) -> None:
    assert pops_listed() == [DENVER]


@pytest.mark.usefixtures("removed")
def test_a_removed_pop_is_no_longer_served(pop_read: Callable[[], Dict[str, Any]]) -> None:
    assert pop_read()["statusCode"] == 404


@pytest.mark.usefixtures("removed")
def test_a_removal_leaves_the_carrier_s_next_pop_where_it_was(lumen: Dict[str, Any]) -> None:
    assert lumen["next_pop"] == {"N": "4"}


@pytest.mark.usefixtures("removed")
def test_a_removal_leaves_the_rest_of_the_carrier_as_it_was(store: SimpleNamespace) -> None:
    under = [item["SK"]["S"] for item in store.items if item["PK"] == {"S": "carriers/1"}]
    assert under == ["pops/1", "fiber-segments/3", "fiber-segments/1"]


@pytest.mark.usefixtures("removed")
def test_a_removal_goes_to_the_table_the_environment_names(store: SimpleNamespace) -> None:
    assert [one["TableName"] for one in store.deletes] == ["store"]


@pytest.mark.usefixtures("removed")
def test_a_removal_deletes_the_pop_under_the_carrier_by_its_id(store: SimpleNamespace) -> None:
    assert [one["Key"] for one in store.deletes] == [
        {"PK": {"S": "carriers/1"}, "SK": {"S": "pops/3"}},
    ]


@pytest.mark.usefixtures("removed")
def test_a_removal_requires_the_pop_to_exist_in_the_store(store: SimpleNamespace) -> None:
    assert store.deletes[0]["ConditionExpression"] == "attribute_exists(PK)"


@pytest.mark.usefixtures("removed")
def test_a_removal_reads_the_carrier_first(store: SimpleNamespace) -> None:
    assert [one["Key"] for one in store.gets] == [{"PK": {"S": "carriers"}, "SK": {"S": "1"}}]


def test_removing_a_pop_of_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(delete_pop("3"))["statusCode"] == 404


def test_removing_a_pop_of_an_unknown_carrier_names_the_carrier(served: Served) -> None:
    assert served(delete_pop("3"))["error"] == "No such carrier"


def test_removing_a_pop_of_an_unknown_carrier_deletes_nothing(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(delete_pop("3"))
    assert store.deletes == []


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_removing_a_pop_of_an_id_that_is_not_a_number_answers_404(
    answer: Handler, carrier: str
) -> None:
    assert answer(delete_pop(carrier))["statusCode"] == 404


def test_removing_an_unknown_pop_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(delete_pop("1", "2"))["statusCode"] == 404


def test_removing_an_unknown_pop_names_the_pop(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(delete_pop("1", "2"))["error"] == "No such pop"


def test_removing_an_unknown_pop_removes_nothing(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(delete_pop("1", "2"))
    assert len(store.items) == len(carriers)


@pytest.mark.parametrize("pop", ["#", "", "3/", "-1"])
def test_removing_a_pop_id_that_is_not_a_number_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], pop: str
) -> None:
    store.items.extend(carriers)
    assert answer(delete_pop("1", pop))["statusCode"] == 404


@pytest.mark.parametrize("pop", ["#", "", "3/", "-1"])
def test_removing_a_pop_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, pop: str
) -> None:
    answer(delete_pop("1", pop))
    assert (store.gets, store.deletes) == ([], [])


def test_a_store_that_refuses_the_removal_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(delete_pop())["statusCode"] == 500


def test_a_store_that_refuses_the_removal_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(delete_pop())["error"] == "Failed to delete the pop"


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**delete_pop(), "httpMethod": "PUT"})["statusCode"] == 404


def test_another_resource_answers_404(answer: Handler) -> None:
    assert answer({**delete_pop(), "resource": "/carriers/{id}/pops"})["statusCode"] == 404
