from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler
from region_events import FRANKFURT, MISPLACED, PHOENIX, REGION_BODY, REGIONS, post

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/create_region"


def test_a_region_is_created_with_201(answer: Handler) -> None:
    assert answer(post(PHOENIX))["statusCode"] == 201


def test_the_first_region_is_number_one(served: Served) -> None:
    assert served(post(PHOENIX)) == {"id": 1, **PHOENIX}


def test_a_region_outside_a_country_with_states_is_created_with_no_state(served: Served) -> None:
    assert served(post(FRANKFURT)) == {"id": 1, **FRANKFURT}


def test_the_created_region_is_located_under_the_collection(answer: Handler) -> None:
    headers = answer(post(PHOENIX))["headers"]
    assert headers["Location"] == "/hyperscale-cloud-service-provider-regions/1"


def test_the_region_id_is_the_next_the_counter_holds(
    served: Served, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    assert served(post(PHOENIX))["id"] == 3


def test_the_regions_counter_moves_past_the_id_it_gave(
    answer: Handler, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    answer(post(PHOENIX))
    assert store.items[0]["next"] == {"N": "4"}


def test_a_region_id_is_never_reused(served: Served) -> None:
    given = [served(post(region))["id"] for region in (PHOENIX, FRANKFURT)]
    assert given == [1, 2]


def test_the_regions_counter_is_advanced_in_the_table_the_environment_names(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(post(PHOENIX))
    assert store.updates[0]["TableName"] == "store"


def test_the_regions_counter_is_the_hash_item_of_the_collection(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(post(PHOENIX))
    assert store.updates[0]["Key"] == {
        "PK": {"S": "hyperscale-cloud-service-provider-regions"}, "SK": {"S": "#"},
    }


def test_the_region_is_written_by_its_id_with_its_place_as_strings_and_numbers(
    answer: Handler, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    answer(post(PHOENIX))
    assert store.items[-1] == {
        "PK": {"S": "hyperscale-cloud-service-provider-regions"}, "SK": {"S": "3"},
        "name": {"S": "Provider C"}, "municipality": {"S": "Phoenix"}, "state": {"S": "AZ"},
        "country": {"S": "US"}, "latitude": {"N": "33.4484"}, "longitude": {"N": "-112.074"},
    }


def test_the_created_region_is_then_listed(answer: Handler, listed: Callable[[], Any]) -> None:
    answer(post(PHOENIX))
    assert listed() == [{"id": 1, **PHOENIX}]


@pytest.mark.parametrize("body", MISPLACED)
def test_a_body_that_is_not_exactly_a_region_answers_400(answer: Handler, body: Any) -> None:
    assert answer(post(body))["statusCode"] == 400


def test_a_body_that_is_not_json_answers_400(answer: Handler) -> None:
    event = {**post({}), "body": "{"}
    assert answer(event)["statusCode"] == 400


def test_a_refused_region_names_what_is_expected(served: Served) -> None:
    assert served(post({}))["error"] == REGION_BODY


def test_a_refused_region_writes_nothing(answer: Handler, store: SimpleNamespace) -> None:
    answer(post({}))
    assert store.items == []


def test_a_store_that_refuses_the_region_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(post(PHOENIX))["statusCode"] == 500


def test_a_store_that_refuses_the_region_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(post(PHOENIX))["error"]
    assert error == "Failed to create the hyperscale cloud service provider region"


def test_a_creation_invalidates_the_collection_and_the_new_region(
    answer: Handler, distribution: SimpleNamespace
) -> None:
    answer(post(PHOENIX))
    assert distribution.invalidated == [[REGIONS, f"{REGIONS}/1"]]


def test_a_region_the_store_refused_invalidates_nothing(
    answer: Handler, store: SimpleNamespace, distribution: SimpleNamespace
) -> None:
    store.failing = True
    answer(post(PHOENIX))
    assert distribution.invalidated == []


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**post(PHOENIX), "httpMethod": "GET"})["statusCode"] == 404


def test_another_resource_answers_404(answer: Handler) -> None:
    event = {**post(PHOENIX), "resource": "/carriers"}
    assert answer(event)["statusCode"] == 404
