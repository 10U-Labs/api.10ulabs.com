from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/delete_carrier"
CARRIER = "/carriers/{id}"


def _delete(carrier: str = "1") -> Dict[str, Any]:
    return {"resource": CARRIER, "httpMethod": "DELETE", "pathParameters": {"id": carrier}}


@pytest.fixture(name="deleted")
def deleted_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    return answer(_delete())


def test_a_stored_carrier_is_deleted_with_204(deleted: Dict[str, Any]) -> None:
    assert deleted["statusCode"] == 204


def test_a_deletion_answers_no_body(deleted: Dict[str, Any]) -> None:
    assert deleted["body"] == ""


@pytest.mark.usefixtures("deleted")
def test_a_deleted_carrier_is_no_longer_listed(listed: Callable[[], Any]) -> None:
    assert listed() == [{"id": 2, "name": "zayo"}]


@pytest.mark.usefixtures("deleted")
def test_everything_under_a_deleted_carrier_goes_with_it(store: SimpleNamespace) -> None:
    assert [item for item in store.items if item["PK"] == {"S": "carriers/1"}] == []


@pytest.mark.usefixtures("deleted")
def test_a_deletion_leaves_the_other_carriers_alone(store: SimpleNamespace) -> None:
    assert [item["SK"]["S"] for item in store.items] == ["#", "2"]


@pytest.mark.usefixtures("deleted")
def test_a_deletion_goes_to_the_table_the_environment_names(store: SimpleNamespace) -> None:
    assert {request["TableName"] for request in store.deletes} == {"store"}


@pytest.mark.usefixtures("deleted")
def test_the_carrier_is_deleted_after_everything_under_it(store: SimpleNamespace) -> None:
    assert [request["Key"] for request in store.deletes] == [
        {"PK": {"S": "carriers/1"}, "SK": {"S": "pops/3"}},
        {"PK": {"S": "carriers/1"}, "SK": {"S": "pops/1"}},
        {"PK": {"S": "carriers/1"}, "SK": {"S": "fiber-segments/3"}},
        {"PK": {"S": "carriers/1"}, "SK": {"S": "fiber-segments/1"}},
        {"PK": {"S": "carriers"}, "SK": {"S": "1"}},
    ]


@pytest.mark.usefixtures("deleted")
def test_deleting_the_carrier_requires_it_to_exist_in_the_store(store: SimpleNamespace) -> None:
    assert store.deletes[-1]["ConditionExpression"] == "attribute_exists(PK)"


def test_deleting_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(_delete("3"))["statusCode"] == 404


def test_deleting_an_unknown_carrier_names_the_error(served: Served) -> None:
    assert served(_delete("3"))["error"] == "No such carrier"


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_deleting_an_id_that_is_not_a_number_answers_404(answer: Handler, carrier: str) -> None:
    assert answer(_delete(carrier))["statusCode"] == 404


def test_deleting_an_id_that_is_not_a_number_deletes_nothing(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_delete("#"))
    assert (store.deletes, len(store.items)) == ([], len(carriers))


def test_a_store_that_refuses_the_deletion_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_delete())["statusCode"] == 500


def test_a_store_that_refuses_the_deletion_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_delete())["error"] == "Failed to delete the carrier"


@pytest.mark.usefixtures("deleted")
def test_a_deletion_invalidates_the_collection_the_carrier_and_everything_under_it(
    distribution: SimpleNamespace
) -> None:
    assert distribution.invalidated == [["/carriers", "/carriers/1", "/carriers/1/*"]]


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**_delete(), "httpMethod": "GET"})["statusCode"] == 404
