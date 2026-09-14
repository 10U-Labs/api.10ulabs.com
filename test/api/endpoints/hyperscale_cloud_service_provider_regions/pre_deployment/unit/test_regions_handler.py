import json
from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

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


PHOENIX = {"name": "us-west-2", "municipality": "Phoenix", "state": "AZ", "country": "US",
           "latitude": 33.4484, "longitude": -112.074}
FRANKFURT = {"name": "eu-central-1", "municipality": "Frankfurt", "state": "", "country": "Germany",
             "latitude": 50.1109, "longitude": 8.6821}
REGION_BODY = (
    'The body must be exactly '
    '{"name", "municipality", "state", "country", "latitude", "longitude"}'
)


def _post(body: Any) -> Dict[str, Any]:
    return {"resource": REGIONS, "httpMethod": "POST", "body": json.dumps(body)}


def _counter(store: SimpleNamespace) -> Dict[str, Any]:
    return next(item for item in store.items if item["SK"] == {"S": "#"})


def test_a_region_is_created_with_201(answer: Handler) -> None:
    assert answer(_post(PHOENIX))["statusCode"] == 201


def test_the_first_region_is_number_one(served: Served) -> None:
    assert served(_post(PHOENIX)) == {"id": 1, **PHOENIX}


def test_a_region_outside_a_country_with_states_is_created_with_no_state(served: Served) -> None:
    assert served(_post(FRANKFURT)) == {"id": 1, **FRANKFURT}


def test_the_created_region_is_located_under_the_collection(answer: Handler) -> None:
    headers = answer(_post(PHOENIX))["headers"]
    assert headers["Location"] == "/hyperscale-cloud-service-provider-regions/1"


def test_the_region_id_is_the_next_the_counter_holds(
    served: Served, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    assert served(_post(PHOENIX))["id"] == 3


def test_the_regions_counter_moves_past_the_id_it_gave(
    answer: Handler, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    answer(_post(PHOENIX))
    assert _counter(store)["next"] == {"N": "4"}


def test_a_region_id_is_never_reused(served: Served) -> None:
    given = [served(_post(region))["id"] for region in (PHOENIX, FRANKFURT)]
    assert given == [1, 2]


def test_the_regions_counter_is_advanced_in_the_table_the_environment_names(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_post(PHOENIX))
    assert store.updates[0]["TableName"] == "store"


def test_the_regions_counter_is_the_hash_item_of_the_collection(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_post(PHOENIX))
    assert store.updates[0]["Key"] == {
        "PK": {"S": "hyperscale-cloud-service-provider-regions"}, "SK": {"S": "#"},
    }


def test_the_region_is_written_by_its_id_with_its_place_as_strings_and_numbers(
    answer: Handler, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    answer(_post(PHOENIX))
    assert store.items[-1] == {
        "PK": {"S": "hyperscale-cloud-service-provider-regions"}, "SK": {"S": "3"},
        "name": {"S": "us-west-2"}, "municipality": {"S": "Phoenix"}, "state": {"S": "AZ"},
        "country": {"S": "US"}, "latitude": {"N": "33.4484"}, "longitude": {"N": "-112.074"},
    }


def test_the_created_region_is_then_listed(answer: Handler, served: Served) -> None:
    answer(_post(PHOENIX))
    assert served(_get()) == [{"id": 1, **PHOENIX}]


MISPLACED = [
    {},
    {**PHOENIX, "id": 9},
    {**PHOENIX, "latitude": "33.4484"},
    {**PHOENIX, "longitude": True},
    {**PHOENIX, "name": ""},
    {**PHOENIX, "municipality": ""},
    {**PHOENIX, "country": ""},
    {**PHOENIX, "state": None},
    dict(list(PHOENIX.items())[:4]),
    [PHOENIX],
]


@pytest.mark.parametrize("body", MISPLACED)
def test_a_body_that_is_not_exactly_a_region_answers_400(answer: Handler, body: Any) -> None:
    assert answer(_post(body))["statusCode"] == 400


def test_a_body_that_is_not_json_answers_400(answer: Handler) -> None:
    event = {**_post({}), "body": "{"}
    assert answer(event)["statusCode"] == 400


def test_a_refused_region_names_what_is_expected(served: Served) -> None:
    assert served(_post({}))["error"] == REGION_BODY


def test_a_refused_region_writes_nothing(answer: Handler, store: SimpleNamespace) -> None:
    answer(_post({}))
    assert store.items == []


def test_a_store_that_refuses_the_region_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_post(PHOENIX))["statusCode"] == 500


def test_a_store_that_refuses_the_region_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(_post(PHOENIX))["error"]
    assert error == "Failed to create the hyperscale cloud service provider region"
