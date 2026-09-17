from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from fiber_segments import DEN_SLC, FIBER_SEGMENT_BODY, LON_PAR, UNSPANNED, post_fiber_segment
from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/add_fiber_segment"


def test_a_fiber_segment_is_added_with_201(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(post_fiber_segment(DEN_SLC))["statusCode"] == 201


def test_a_submarine_fiber_segment_between_stateless_ends_is_added_with_201(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(post_fiber_segment(LON_PAR))["statusCode"] == 201


def test_a_submarine_fiber_segment_answers_as_submarine_with_no_states(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(post_fiber_segment(LON_PAR)) == {"id": 4, **LON_PAR}


def test_the_added_fiber_segment_answers_with_the_id_the_carrier_holds_next(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(post_fiber_segment(DEN_SLC)) == {"id": 4, **DEN_SLC}


def test_the_added_fiber_segment_is_located_under_the_carrier_s_fiber_segments(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    headers = answer(post_fiber_segment(DEN_SLC))["headers"]
    assert headers["Location"] == "/carriers/1/fiber-segments/4"


@pytest.fixture(name="added_to")
def added_to_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], lumen: Dict[str, Any]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(post_fiber_segment(DEN_SLC))
    return lumen


def test_the_carrier_s_next_fiber_segment_moves_past_the_id_it_gave(
    added_to: Dict[str, Any]
) -> None:
    assert added_to["next_fiber_segment"] == {"N": "5"}


def test_adding_a_fiber_segment_leaves_the_carrier_s_next_pop_where_it_was(
    added_to: Dict[str, Any]
) -> None:
    assert added_to["next_pop"] == {"N": "4"}


def test_a_fiber_segment_id_is_never_reused(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    spans = (DEN_SLC, {**DEN_SLC, "z_municipality": "Cheyenne", "z_state": "WY"})
    assert [served(post_fiber_segment(span, "2"))["id"] for span in spans] == [1, 2]


def test_the_fiber_segment_is_written_under_the_carrier_by_its_id(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(post_fiber_segment(DEN_SLC))
    assert store.items[-1] == {
        "PK": {"S": "carriers/1"}, "SK": {"S": "fiber-segments/4"},
        "a_municipality": {"S": "Denver"}, "a_state": {"S": "CO"},
        "z_municipality": {"S": "Salt Lake City"}, "z_state": {"S": "UT"},
        "submarine": {"BOOL": False},
    }


def test_the_added_fiber_segment_is_then_listed_last(
    answer: Handler, fiber_segments_listed: Callable[[], Any], store: SimpleNamespace,
    carriers: List[Dict[str, Any]],
) -> None:
    store.items.extend(carriers)
    answer(post_fiber_segment(DEN_SLC))
    assert fiber_segments_listed()[-1] == {"id": 4, **DEN_SLC}


@pytest.fixture(name="fiber_segment_request")
def fiber_segment_request_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(post_fiber_segment(DEN_SLC))
    return dict(store.updates[0])


def test_a_fiber_segment_id_is_taken_in_the_table_the_environment_names(
    fiber_segment_request: Dict[str, Any]
) -> None:
    assert fiber_segment_request["TableName"] == "store"


def test_a_fiber_segment_id_is_taken_from_the_carrier_s_own_item(
    fiber_segment_request: Dict[str, Any]
) -> None:
    assert fiber_segment_request["Key"] == {"PK": {"S": "carriers"}, "SK": {"S": "1"}}


def test_a_fiber_segment_id_is_taken_from_the_carrier_s_next_fiber_segment(
    fiber_segment_request: Dict[str, Any]
) -> None:
    assert fiber_segment_request["ExpressionAttributeNames"] == {"#next": "next_fiber_segment"}


def test_taking_a_fiber_segment_id_requires_the_carrier_to_exist_in_the_store(
    fiber_segment_request: Dict[str, Any]
) -> None:
    assert fiber_segment_request["ConditionExpression"] == "attribute_exists(PK)"


def test_adding_a_fiber_segment_to_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(post_fiber_segment(DEN_SLC, "3"))["statusCode"] == 404


def test_adding_a_fiber_segment_to_an_unknown_carrier_names_the_error(served: Served) -> None:
    assert served(post_fiber_segment(DEN_SLC, "3"))["error"] == "No such carrier"


def test_adding_a_fiber_segment_to_an_unknown_carrier_writes_nothing(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(post_fiber_segment(DEN_SLC, "3"))
    assert store.items == []


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_adding_a_fiber_segment_to_an_id_that_is_not_a_number_answers_404(
    answer: Handler, carrier: str
) -> None:
    assert answer(post_fiber_segment(DEN_SLC, carrier))["statusCode"] == 404


@pytest.mark.parametrize("body", UNSPANNED)
def test_a_fiber_segment_that_is_not_exactly_a_span_answers_400(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], body: Any
) -> None:
    store.items.extend(carriers)
    assert answer(post_fiber_segment(body))["statusCode"] == 400


def test_a_fiber_segment_that_is_not_json_answers_400(answer: Handler) -> None:
    event = {**post_fiber_segment({}), "body": "{"}
    assert answer(event)["statusCode"] == 400


def test_a_refused_fiber_segment_names_what_is_expected(served: Served) -> None:
    assert served(post_fiber_segment({}))["error"] == FIBER_SEGMENT_BODY


def test_a_refused_fiber_segment_changes_nothing(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(post_fiber_segment({}))
    assert (store.updates, len(store.items)) == ([], len(carriers))


def test_a_store_that_refuses_the_fiber_segment_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(post_fiber_segment(DEN_SLC))["statusCode"] == 500


def test_a_store_that_refuses_the_fiber_segment_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(post_fiber_segment(DEN_SLC))["error"] == "Failed to add the fiber segment"


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**post_fiber_segment(DEN_SLC), "httpMethod": "GET"})["statusCode"] == 404


def test_another_resource_answers_404(answer: Handler) -> None:
    assert answer({**post_fiber_segment(DEN_SLC), "resource": "/carriers"})["statusCode"] == 404
