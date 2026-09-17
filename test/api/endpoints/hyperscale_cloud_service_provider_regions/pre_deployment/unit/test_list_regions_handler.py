from types import SimpleNamespace
from typing import Any, Callable, Dict, List

from lambda_http import Handler
from region_events import COLUMBUS, DUBLIN, get

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/list_regions"


def test_an_empty_store_answers_no_regions(served: Served) -> None:
    assert served(get()) == []


def test_an_empty_store_answers_200(answer: Handler) -> None:
    assert answer(get())["statusCode"] == 200


def test_the_regions_answer_by_id_and_place_in_id_order(
    served: Served, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    assert served(get()) == [COLUMBUS, DUBLIN]


def test_the_regions_are_read_from_the_table_the_environment_names(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(get())
    assert store.queries[0]["TableName"] == "store"


def test_the_regions_are_read_from_their_own_partition(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(get())
    assert store.queries[0]["ExpressionAttributeValues"] == {
        ":pk": {"S": "hyperscale-cloud-service-provider-regions"},
    }


def test_a_store_that_refuses_the_regions_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(get())["statusCode"] == 500


def test_a_store_that_refuses_the_regions_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(get())["error"]
    assert error == "Failed to read the hyperscale cloud service provider regions"


def test_another_route_answers_404(answer: Handler) -> None:
    assert answer(get("/carriers"))["statusCode"] == 404
