from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler
from region_events import DUBLIN, MISSING, get_one

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/read_region"


def test_a_stored_region_answers_200(
    answer: Handler, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    assert answer(get_one("2"))["statusCode"] == 200


def test_a_stored_region_answers_by_its_id_and_place(
    served: Served, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    assert served(get_one("2")) == DUBLIN


def test_a_region_is_read_from_the_table_the_environment_names(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(get_one("2"))
    assert store.gets[0]["TableName"] == "store"


def test_a_region_is_read_by_its_key_in_the_collection(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(get_one("2"))
    assert store.gets[0]["Key"] == {
        "PK": {"S": "hyperscale-cloud-service-provider-regions"}, "SK": {"S": "2"},
    }


def test_an_unknown_region_answers_404(
    answer: Handler, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    assert answer(get_one("3"))["statusCode"] == 404


def test_an_unknown_region_names_the_error(served: Served) -> None:
    assert served(get_one("3"))["error"] == MISSING


@pytest.mark.parametrize("region", ["#", "", "Provider A", "-1"])
def test_a_region_id_that_is_not_a_number_answers_404(answer: Handler, region: str) -> None:
    assert answer(get_one(region))["statusCode"] == 404


def test_the_regions_counter_is_never_asked_for_as_a_region(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(get_one("#"))
    assert store.gets == []


def test_a_store_that_refuses_the_region_read_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(get_one("1"))["statusCode"] == 500


def test_a_store_that_refuses_the_region_read_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(get_one("1"))["error"]
    assert error == "Failed to read the hyperscale cloud service provider region"


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**get_one("2"), "httpMethod": "PUT"})["statusCode"] == 404


def test_another_resource_answers_404(answer: Handler) -> None:
    event = {**get_one("2"), "resource": "/hyperscale-cloud-service-provider-regions"}
    assert answer(event)["statusCode"] == 404
