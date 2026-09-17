import json
from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler
from region_events import (
    COLUMBUS, DUBLIN, MISPLACED, MISSING, PHOENIX, REGION_BODY, REGIONS, put,
)

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/correct_region"


def test_a_stored_region_is_corrected_with_200(
    answer: Handler, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    assert answer(put(PHOENIX))["statusCode"] == 200


def test_a_corrected_region_answers_by_its_id_and_new_place(
    served: Served, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    assert served(put(PHOENIX)) == {"id": 2, **PHOENIX}


def test_a_corrected_region_is_then_served_at_its_own_url(
    answer: Handler, region_read: Callable[[], Dict[str, Any]], store: SimpleNamespace,
    regions: List[Dict[str, Any]],
) -> None:
    store.items.extend(regions)
    answer(put(PHOENIX))
    assert json.loads(region_read()["body"]) == {"id": 2, **PHOENIX}


def test_a_correction_leaves_the_other_regions_as_they_were(
    answer: Handler, listed: Callable[[], Any], store: SimpleNamespace,
    regions: List[Dict[str, Any]],
) -> None:
    store.items.extend(regions)
    answer(put(PHOENIX))
    assert listed() == [COLUMBUS, {"id": 2, **PHOENIX}]


def test_a_correction_leaves_the_regions_counter_where_it_was(
    answer: Handler, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    answer(put(PHOENIX))
    assert store.items[0]["next"] == {"N": "3"}


@pytest.fixture(name="region_correction")
def region_correction_fixture(
    answer: Handler, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(regions)
    answer(put(PHOENIX))
    return dict(store.puts[0])


def test_a_region_correction_goes_to_the_table_the_environment_names(
    region_correction: Dict[str, Any]
) -> None:
    assert region_correction["TableName"] == "store"


def test_a_region_correction_rewrites_the_region_by_its_id(
    region_correction: Dict[str, Any]
) -> None:
    assert region_correction["Item"] == {
        "PK": {"S": "hyperscale-cloud-service-provider-regions"}, "SK": {"S": "2"},
        **{field: {"S": PHOENIX[field]} for field in ("name", "municipality", "state", "country")},
        "latitude": {"N": "33.4484"}, "longitude": {"N": "-112.074"},
    }


def test_a_region_correction_requires_the_region_to_exist_in_the_store(
    region_correction: Dict[str, Any]
) -> None:
    assert region_correction["ConditionExpression"] == "attribute_exists(PK)"


def test_correcting_an_unknown_region_answers_404(
    answer: Handler, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    assert answer(put(PHOENIX, "3"))["statusCode"] == 404


def test_correcting_an_unknown_region_names_the_region(served: Served) -> None:
    assert served(put(PHOENIX, "3"))["error"] == MISSING


def test_correcting_an_unknown_region_adds_none(
    answer: Handler, store: SimpleNamespace, regions: List[Dict[str, Any]]
) -> None:
    store.items.extend(regions)
    answer(put(PHOENIX, "3"))
    assert len(store.items) == len(regions)


@pytest.mark.parametrize("region", ["#", "", "Provider A", "-1"])
def test_correcting_a_region_id_that_is_not_a_number_answers_404(
    answer: Handler, region: str
) -> None:
    assert answer(put(PHOENIX, region))["statusCode"] == 404


@pytest.mark.parametrize("region", ["#", "", "Provider A", "-1"])
def test_correcting_a_region_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, region: str
) -> None:
    answer(put(PHOENIX, region))
    assert store.puts == []


@pytest.mark.parametrize("body", MISPLACED)
def test_a_region_correction_that_is_not_exactly_a_region_answers_400(
    answer: Handler, store: SimpleNamespace, regions: List[Dict[str, Any]], body: Any
) -> None:
    store.items.extend(regions)
    assert answer(put(body))["statusCode"] == 400


def test_a_region_correction_that_is_not_json_answers_400(answer: Handler) -> None:
    assert answer({**put({}), "body": "{"})["statusCode"] == 400


def test_a_refused_region_correction_names_what_is_expected(served: Served) -> None:
    assert served(put({}))["error"] == REGION_BODY


def test_a_refused_region_correction_changes_nothing(
    region_read: Callable[[], Dict[str, Any]], served: Served, store: SimpleNamespace,
    regions: List[Dict[str, Any]],
) -> None:
    store.items.extend(regions)
    refusal = served(put({}))["error"]
    assert (refusal, store.puts, json.loads(region_read()["body"])) == (REGION_BODY, [], DUBLIN)


def test_a_store_that_refuses_the_region_correction_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(put(PHOENIX))["statusCode"] == 500


def test_a_store_that_refuses_the_region_correction_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(put(PHOENIX))["error"]
    assert error == "Failed to update the hyperscale cloud service provider region"


def test_a_correction_invalidates_the_collection_and_the_region(
    answer: Handler, store: SimpleNamespace, regions: List[Dict[str, Any]],
    distribution: SimpleNamespace,
) -> None:
    store.items.extend(regions)
    answer(put(PHOENIX))
    assert distribution.invalidated == [[REGIONS, f"{REGIONS}/2"]]


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**put(PHOENIX), "httpMethod": "GET"})["statusCode"] == 404


def test_another_resource_answers_404(answer: Handler) -> None:
    event = {**put(PHOENIX), "resource": "/hyperscale-cloud-service-provider-regions"}
    assert answer(event)["statusCode"] == 404
