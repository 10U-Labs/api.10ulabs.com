import json
from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from fiber_segments import (
    DEN_ORD, DEN_SLC, FIBER_SEGMENT_BODY, LON_PAR, NYC_AMS, UNSPANNED, put_fiber_segment,
)
from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/correct_fiber_segment"


def test_a_stored_fiber_segment_is_corrected_with_200(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(put_fiber_segment(DEN_SLC))["statusCode"] == 200


def test_a_corrected_fiber_segment_answers_by_its_id_and_new_span(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(put_fiber_segment(DEN_SLC)) == {"id": 3, **DEN_SLC}


def test_a_fiber_segment_corrected_to_a_submarine_span_answers_as_submarine_with_no_states(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(put_fiber_segment(LON_PAR, "1", "1")) == {"id": 1, **LON_PAR}


def test_a_corrected_fiber_segment_is_then_served_at_its_own_url(
    answer: Handler, fiber_segment_read: Callable[[], Dict[str, Any]], store: SimpleNamespace,
    carriers: List[Dict[str, Any]],
) -> None:
    store.items.extend(carriers)
    answer(put_fiber_segment(DEN_SLC))
    assert json.loads(fiber_segment_read()["body"]) == {"id": 3, **DEN_SLC}


def test_a_correction_leaves_the_carrier_s_other_fiber_segments_as_they_were(
    answer: Handler, fiber_segments_listed: Callable[[], Any], store: SimpleNamespace,
    carriers: List[Dict[str, Any]],
) -> None:
    store.items.extend(carriers)
    answer(put_fiber_segment(DEN_SLC))
    assert fiber_segments_listed() == [DEN_ORD, {"id": 3, **DEN_SLC}]


def test_a_correction_leaves_the_carrier_s_next_fiber_segment_where_it_was(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], lumen: Dict[str, Any]
) -> None:
    store.items.extend(carriers)
    answer(put_fiber_segment(DEN_SLC))
    assert lumen["next_fiber_segment"] == {"N": "4"}


@pytest.fixture(name="span_correction")
def span_correction_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(put_fiber_segment(DEN_SLC))
    return dict(store.puts[0])


def test_a_span_correction_goes_to_the_table_the_environment_names(
    span_correction: Dict[str, Any]
) -> None:
    assert span_correction["TableName"] == "store"


def test_a_span_correction_rewrites_the_fiber_segment_under_the_carrier_by_its_id(
    span_correction: Dict[str, Any]
) -> None:
    assert span_correction["Item"] == {
        "PK": {"S": "carriers/1"}, "SK": {"S": "fiber-segments/3"},
        **{field: {"S": end} for field, end in DEN_SLC.items() if field != "submarine"},
        "submarine": {"BOOL": False},
    }


def test_a_span_correction_requires_the_fiber_segment_to_exist_in_the_store(
    span_correction: Dict[str, Any]
) -> None:
    assert span_correction["ConditionExpression"] == "attribute_exists(PK)"


def test_a_span_correction_reads_the_carrier_first(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(put_fiber_segment(DEN_SLC))
    assert [one["Key"] for one in store.gets] == [{"PK": {"S": "carriers"}, "SK": {"S": "1"}}]


def test_correcting_a_fiber_segment_of_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(put_fiber_segment(DEN_SLC, "3"))["statusCode"] == 404


def test_correcting_a_fiber_segment_of_an_unknown_carrier_names_the_carrier(
    served: Served
) -> None:
    assert served(put_fiber_segment(DEN_SLC, "3"))["error"] == "No such carrier"


def test_correcting_a_fiber_segment_of_an_unknown_carrier_writes_nothing(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(put_fiber_segment(DEN_SLC, "3"))
    assert store.puts == []


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_correcting_a_fiber_segment_of_an_id_that_is_not_a_number_answers_404(
    answer: Handler, carrier: str
) -> None:
    assert answer(put_fiber_segment(DEN_SLC, carrier))["statusCode"] == 404


def test_correcting_an_unknown_fiber_segment_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(put_fiber_segment(DEN_SLC, "1", "2"))["statusCode"] == 404


def test_correcting_an_unknown_fiber_segment_names_the_fiber_segment(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(put_fiber_segment(DEN_SLC, "1", "2"))["error"] == "No such fiber segment"


def test_correcting_an_unknown_fiber_segment_adds_none(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(put_fiber_segment(DEN_SLC, "1", "2"))
    assert len(store.items) == len(carriers)


@pytest.mark.parametrize("fiber_segment", ["#", "", "3/", "-1"])
def test_correcting_a_fiber_segment_id_that_is_not_a_number_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], fiber_segment: str
) -> None:
    store.items.extend(carriers)
    assert answer(put_fiber_segment(DEN_SLC, "1", fiber_segment))["statusCode"] == 404


@pytest.mark.parametrize("fiber_segment", ["#", "", "3/", "-1"])
def test_correcting_a_fiber_segment_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, fiber_segment: str
) -> None:
    answer(put_fiber_segment(DEN_SLC, "1", fiber_segment))
    assert (store.gets, store.puts) == ([], [])


@pytest.mark.parametrize("body", UNSPANNED)
def test_a_span_correction_that_is_not_exactly_a_span_answers_400(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], body: Any
) -> None:
    store.items.extend(carriers)
    assert answer(put_fiber_segment(body))["statusCode"] == 400


def test_a_span_correction_that_is_not_json_answers_400(answer: Handler) -> None:
    event = {**put_fiber_segment({}), "body": "{"}
    assert answer(event)["statusCode"] == 400


def test_a_refused_span_correction_names_what_is_expected(served: Served) -> None:
    assert served(put_fiber_segment({}))["error"] == FIBER_SEGMENT_BODY


def test_a_refused_span_correction_changes_nothing(
    fiber_segment_read: Callable[[], Dict[str, Any]], served: Served, store: SimpleNamespace,
    carriers: List[Dict[str, Any]],
) -> None:
    store.items.extend(carriers)
    refusal = served(put_fiber_segment({}))["error"]
    assert (refusal, store.puts, json.loads(fiber_segment_read()["body"])) == (
        FIBER_SEGMENT_BODY, [], NYC_AMS
    )


def test_a_store_that_refuses_the_span_correction_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(put_fiber_segment(DEN_SLC))["statusCode"] == 500


def test_a_store_that_refuses_the_span_correction_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(put_fiber_segment(DEN_SLC))["error"] == "Failed to update the fiber segment"


def test_a_corrected_fiber_segment_invalidates_the_carrier_s_fiber_segments_and_its_own_url(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]],
    distribution: SimpleNamespace,
) -> None:
    store.items.extend(carriers)
    answer(put_fiber_segment(DEN_SLC))
    assert distribution.invalidated == [
        ["/carriers/1/fiber-segments", "/carriers/1/fiber-segments/3"]
    ]


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**put_fiber_segment(DEN_SLC), "httpMethod": "POST"})["statusCode"] == 404


def test_another_resource_answers_404(answer: Handler) -> None:
    assert answer({**put_fiber_segment(DEN_SLC), "resource": "/carriers/{id}"})["statusCode"] == 404
