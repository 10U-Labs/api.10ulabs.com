from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler
from region_events import COLUMBUS, MISSING, delete

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/delete_region"


@pytest.fixture(name="region_removed")
def region_removed_fixture(
    answer: Handler, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(regions)
    return answer(delete())


def test_a_stored_region_is_removed_with_204(region_removed: Dict[str, Any]) -> None:
    assert region_removed["statusCode"] == 204


def test_a_region_removal_answers_no_content(region_removed: Dict[str, Any]) -> None:
    assert region_removed["body"] == ""


@pytest.mark.usefixtures("region_removed")
def test_a_removed_region_is_no_longer_listed(listed: Callable[[], Any]) -> None:
    assert listed() == [COLUMBUS]


@pytest.mark.usefixtures("region_removed")
def test_a_removed_region_is_no_longer_served(region_read: Callable[[], Dict[str, Any]]) -> None:
    assert region_read()["statusCode"] == 404


@pytest.mark.usefixtures("region_removed")
def test_a_region_removal_leaves_the_regions_counter_where_it_was(store: SimpleNamespace) -> None:
    assert store.items[0]["next"] == {"N": "3"}


@pytest.mark.usefixtures("region_removed")
def test_a_region_removal_goes_to_the_table_the_environment_names(store: SimpleNamespace) -> None:
    assert [one["TableName"] for one in store.deletes] == ["store"]


@pytest.mark.usefixtures("region_removed")
def test_a_region_removal_deletes_the_region_by_its_key(store: SimpleNamespace) -> None:
    assert [one["Key"] for one in store.deletes] == [
        {"PK": {"S": "hyperscale-cloud-service-provider-regions"}, "SK": {"S": "2"}},
    ]


@pytest.mark.usefixtures("region_removed")
def test_a_region_removal_requires_the_region_to_exist_in_the_store(
    store: SimpleNamespace
) -> None:
    assert store.deletes[0]["ConditionExpression"] == "attribute_exists(PK)"


def test_removing_an_unknown_region_answers_404(
    answer: Handler, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    assert answer(delete("3"))["statusCode"] == 404


def test_removing_an_unknown_region_names_the_region(served: Served) -> None:
    assert served(delete("3"))["error"] == MISSING


def test_removing_an_unknown_region_removes_nothing(
    answer: Handler, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    answer(delete("3"))
    assert len(store.items) == len(regions)


@pytest.mark.parametrize("region", ["#", "", "Provider A", "-1"])
def test_removing_a_region_id_that_is_not_a_number_answers_404(
    answer: Handler, region: str
) -> None:
    assert answer(delete(region))["statusCode"] == 404


@pytest.mark.parametrize("region", ["#", "", "Provider A", "-1"])
def test_removing_a_region_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, region: str
) -> None:
    answer(delete(region))
    assert store.deletes == []


def test_a_store_that_refuses_the_region_removal_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(delete())["statusCode"] == 500


def test_a_store_that_refuses_the_region_removal_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(delete())["error"]
    assert error == "Failed to delete the hyperscale cloud service provider region"


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**delete(), "httpMethod": "GET"})["statusCode"] == 404


def test_another_resource_answers_404(answer: Handler) -> None:
    event = {**delete(), "resource": "/hyperscale-cloud-service-provider-regions"}
    assert answer(event)["statusCode"] == 404
