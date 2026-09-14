from types import SimpleNamespace
from typing import Any, Callable, Dict, List

from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
REGIONS = "/hyperscale-cloud-service-provider-regions"
COLUMBUS = {"id": 1, "name": "us-east-2", "municipality": "Columbus", "state": "OH",
            "country": "US", "latitude": 39.9612, "longitude": -82.9988}
DUBLIN = {"id": 2, "name": "eu-west-1", "municipality": "Dublin", "state": "",
          "country": "Ireland", "latitude": 53.3498, "longitude": -6.2603}


def _get(resource: str = REGIONS) -> Dict[str, Any]:
    return {"resource": resource, "httpMethod": "GET"}


def test_an_empty_store_answers_no_regions(served: Served) -> None:
    assert served(_get()) == []


def test_an_empty_store_answers_200(answer: Handler) -> None:
    assert answer(_get())["statusCode"] == 200


def test_the_regions_answer_by_id_and_place_in_id_order(
    served: Served, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    assert served(_get()) == [COLUMBUS, DUBLIN]


def test_the_regions_are_read_from_the_table_the_environment_names(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_get())
    assert store.queries[0]["TableName"] == "store"


def test_the_regions_are_read_from_their_own_partition(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_get())
    assert store.queries[0]["ExpressionAttributeValues"] == {
        ":pk": {"S": "hyperscale-cloud-service-provider-regions"},
    }


def test_a_store_that_refuses_the_regions_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_get())["statusCode"] == 500


def test_a_store_that_refuses_the_regions_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(_get())["error"]
    assert error == "Failed to read the hyperscale cloud service provider regions"


def test_another_route_answers_404(answer: Handler) -> None:
    assert answer(_get("/carriers"))["statusCode"] == 404
