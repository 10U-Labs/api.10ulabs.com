from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from fiber_segments import (
    DEN_SLC, DEN_SLC_ITEM, FIBER_SEGMENTS_BODY, LON_PAR, UNSPANNED, put_fiber_segments,
)
from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/replace_fiber_segments"
RESPANNED = [{"id": 4, **DEN_SLC}, {"id": 5, **LON_PAR}]


@pytest.fixture(name="respanned")
def respanned_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    return answer(put_fiber_segments([DEN_SLC, LON_PAR]))


def test_a_carrier_s_fiber_segments_are_replaced_with_200(respanned: Dict[str, Any]) -> None:
    assert respanned["statusCode"] == 200


def test_a_replacement_answers_the_new_fiber_segments_under_fresh_ids(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(put_fiber_segments([DEN_SLC, LON_PAR])) == RESPANNED


@pytest.mark.usefixtures("respanned")
def test_the_new_fiber_segments_are_then_listed_in_place_of_the_old(
    fiber_segments_listed: Callable[[], Any],
) -> None:
    assert fiber_segments_listed() == RESPANNED


@pytest.mark.usefixtures("respanned")
def test_a_replaced_fiber_segment_is_no_longer_served(
    fiber_segment_read: Callable[[], Dict[str, Any]],
) -> None:
    assert fiber_segment_read()["statusCode"] == 404


@pytest.mark.usefixtures("respanned")
def test_the_carrier_s_next_fiber_segment_moves_past_the_ids_it_gave(
    lumen: Dict[str, Any],
) -> None:
    assert lumen["next_fiber_segment"] == {"N": "6"}


@pytest.mark.usefixtures("respanned")
def test_a_replacement_leaves_the_carrier_s_pops_as_they_were(store: SimpleNamespace) -> None:
    kept = [item["SK"]["S"] for item in store.items if item["PK"] == {"S": "carriers/1"}]
    assert [key for key in kept if key.startswith("pops/")] == ["pops/3", "pops/1"]


@pytest.mark.usefixtures("respanned")
def test_a_new_fiber_segment_is_written_under_the_carrier_by_its_id(
    store: SimpleNamespace,
) -> None:
    assert store.items[-2] == DEN_SLC_ITEM


@pytest.mark.usefixtures("respanned")
def test_a_respan_writes_to_the_table_the_environment_names(store: SimpleNamespace) -> None:
    assert {name for written in store.batches for name in written["RequestItems"]} == {"store"}


@pytest.mark.usefixtures("respanned")
def test_a_respan_takes_its_ids_from_the_carrier_s_own_item(store: SimpleNamespace) -> None:
    assert [taken["Key"] for taken in store.updates] == [
        {"PK": {"S": "carriers"}, "SK": {"S": "1"}},
    ]


@pytest.mark.usefixtures("respanned")
def test_a_respan_takes_one_id_for_each_fiber_segment_in_one_update(
    store: SimpleNamespace,
) -> None:
    assert store.updates[0]["ExpressionAttributeValues"][":count"] == {"N": "2"}


@pytest.mark.usefixtures("respanned")
def test_a_respan_requires_the_carrier_to_exist_in_the_store(store: SimpleNamespace) -> None:
    assert store.updates[0]["ConditionExpression"] == "attribute_exists(PK)"


@pytest.mark.usefixtures("respanned")
def test_a_respan_invalidates_the_carrier_s_fiber_segments_once(
    distribution: SimpleNamespace,
) -> None:
    assert distribution.invalidated == [
        ["/carriers/1/fiber-segments", "/carriers/1/fiber-segments/*"],
    ]


def test_a_respan_longer_than_a_batch_is_stored_whole(
    answer: Handler, fiber_segments_listed: Callable[[], Any], store: SimpleNamespace,
    carriers: List[Dict[str, Any]],
) -> None:
    store.items.extend(carriers)
    spans = [{**DEN_SLC, "z_municipality": f"Town {number}"} for number in range(30)]
    answer(put_fiber_segments(spans))
    assert len(fiber_segments_listed()) == 30


@pytest.fixture(name="unspanned")
def unspanned_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    return answer(put_fiber_segments([]))


def test_no_fiber_segments_answers_an_empty_list(unspanned: Dict[str, Any]) -> None:
    assert unspanned["body"] == "[]"


@pytest.mark.usefixtures("unspanned")
def test_no_fiber_segments_removes_every_fiber_segment_of_the_carrier(
    fiber_segments_listed: Callable[[], Any],
) -> None:
    assert fiber_segments_listed() == []


@pytest.mark.usefixtures("unspanned")
def test_no_fiber_segments_leaves_the_carrier_s_next_fiber_segment_where_it_was(
    lumen: Dict[str, Any],
) -> None:
    assert lumen["next_fiber_segment"] == {"N": "4"}


def test_respanning_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(put_fiber_segments([DEN_SLC], "3"))["statusCode"] == 404


def test_respanning_an_unknown_carrier_names_the_error(served: Served) -> None:
    assert served(put_fiber_segments([DEN_SLC], "3"))["error"] == "No such carrier"


def test_respanning_an_unknown_carrier_writes_nothing(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(put_fiber_segments([DEN_SLC], "3"))
    assert (store.items, store.batches) == ([], [])


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_respanning_an_id_that_is_not_a_number_answers_404(answer: Handler, carrier: str) -> None:
    assert answer(put_fiber_segments([DEN_SLC], carrier))["statusCode"] == 404


@pytest.mark.parametrize(
    "spans", [{}, DEN_SLC, None, "Denver", *[[DEN_SLC, span] for span in UNSPANNED]]
)
def test_a_body_that_is_not_a_list_of_spans_answers_400(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], spans: Any
) -> None:
    store.items.extend(carriers)
    assert answer(put_fiber_segments(spans))["statusCode"] == 400


def test_spans_that_are_not_json_answer_400(answer: Handler) -> None:
    unparsed = {**put_fiber_segments([]), "body": "[{"}
    assert answer(unparsed)["statusCode"] == 400


def test_refused_spans_name_what_is_expected(served: Served) -> None:
    assert served(put_fiber_segments({}))["error"] == FIBER_SEGMENTS_BODY


def test_refused_spans_change_nothing(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(put_fiber_segments([DEN_SLC, {}]))
    assert (len(store.items), store.batches, store.updates) == (len(carriers), [], [])


def test_a_store_that_refuses_the_spans_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(put_fiber_segments([LON_PAR]))["statusCode"] == 500


def test_a_store_that_refuses_the_spans_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(put_fiber_segments([LON_PAR]))["error"] == "Failed to replace the fiber segments"


def test_another_verb_on_the_fiber_segments_answers_404(answer: Handler) -> None:
    event = {**put_fiber_segments([LON_PAR]), "httpMethod": "PATCH"}
    assert answer(event)["statusCode"] == 404


def test_another_resource_than_the_fiber_segments_answers_404(answer: Handler) -> None:
    event = {**put_fiber_segments([LON_PAR]), "resource": "/carriers"}
    assert answer(event)["statusCode"] == 404
