import json
from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
FIBER_SEGMENTS = "/carriers/{carrier}/fiber-segments"
DEN_ORD = {"id": 1, "a_municipality": "Denver", "a_state": "CO",
           "z_municipality": "Chicago", "z_state": "IL", "submarine": False}
NYC_AMS = {"id": 3, "a_municipality": "New York", "a_state": "NY",
           "z_municipality": "Amsterdam", "z_state": "", "submarine": True}


def _get_fiber_segments(carrier: str = "1") -> Dict[str, Any]:
    event = {"resource": FIBER_SEGMENTS, "httpMethod": "GET"}
    return {**event, "pathParameters": {"carrier": carrier}}


def test_the_fiber_segments_of_a_stored_carrier_answer_200(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_get_fiber_segments())["statusCode"] == 200


def test_the_fiber_segments_answer_as_spans_in_id_order(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_get_fiber_segments()) == [DEN_ORD, NYC_AMS]


def test_a_carrier_without_fiber_segments_answers_none(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_get_fiber_segments("2")) == []


@pytest.fixture(name="fiber_segments_query")
def fiber_segments_query_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(_get_fiber_segments())
    return dict(store.queries[-1])


def test_the_fiber_segments_are_read_from_under_the_carrier(
    fiber_segments_query: Dict[str, Any]
) -> None:
    assert fiber_segments_query["ExpressionAttributeValues"] == {
        ":pk": {"S": "carriers/1"}, ":prefix": {"S": "fiber-segments/"},
    }


def test_the_fiber_segments_are_read_from_the_table_the_environment_names(
    fiber_segments_query: Dict[str, Any]
) -> None:
    assert fiber_segments_query["TableName"] == "store"


def test_the_fiber_segments_are_read_after_the_carrier(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_get_fiber_segments())
    assert [one["Key"] for one in store.gets] == [{"PK": {"S": "carriers"}, "SK": {"S": "1"}}]


def test_the_fiber_segments_of_an_unknown_carrier_answer_404(answer: Handler) -> None:
    assert answer(_get_fiber_segments("3"))["statusCode"] == 404


def test_the_fiber_segments_of_an_unknown_carrier_name_the_error(served: Served) -> None:
    assert served(_get_fiber_segments("3"))["error"] == "No such carrier"


def test_the_fiber_segments_of_an_unknown_carrier_are_not_looked_for(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_get_fiber_segments("3"))
    assert store.queries == []


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_the_fiber_segments_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, carrier: str
) -> None:
    assert answer(_get_fiber_segments(carrier))["statusCode"] == 404


def test_a_store_that_refuses_the_fiber_segments_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_get_fiber_segments())["statusCode"] == 500


def test_a_store_that_refuses_the_fiber_segments_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_fiber_segments())["error"] == "Failed to read the fiber segments"


DEN_SLC = {"a_municipality": "Denver", "a_state": "CO",
           "z_municipality": "Salt Lake City", "z_state": "UT", "submarine": False}
LON_PAR = {"a_municipality": "London", "a_state": "",
           "z_municipality": "Paris", "z_state": "", "submarine": True}
FIBER_SEGMENT_BODY = (
    'The body must be exactly '
    '{"a_municipality", "a_state", "z_municipality", "z_state", "submarine"}'
)


def _post_fiber_segment(body: Any, carrier: str = "1") -> Dict[str, Any]:
    event = {"resource": FIBER_SEGMENTS, "httpMethod": "POST", "body": json.dumps(body)}
    return {**event, "pathParameters": {"carrier": carrier}}


def test_a_fiber_segment_is_added_with_201(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_post_fiber_segment(DEN_SLC))["statusCode"] == 201


def test_a_submarine_fiber_segment_between_stateless_ends_is_added_with_201(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_post_fiber_segment(LON_PAR))["statusCode"] == 201


def test_a_submarine_fiber_segment_answers_as_submarine_with_no_states(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_post_fiber_segment(LON_PAR)) == {"id": 4, **LON_PAR}


def test_the_added_fiber_segment_answers_with_the_id_the_carrier_holds_next(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_post_fiber_segment(DEN_SLC)) == {"id": 4, **DEN_SLC}


def test_the_added_fiber_segment_is_located_under_the_carrier_s_fiber_segments(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    headers = answer(_post_fiber_segment(DEN_SLC))["headers"]
    assert headers["Location"] == "/carriers/1/fiber-segments/4"


@pytest.fixture(name="added_to")
def added_to_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], lumen: Dict[str, Any]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(_post_fiber_segment(DEN_SLC))
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
    assert [served(_post_fiber_segment(span, "2"))["id"] for span in spans] == [1, 2]


def test_the_fiber_segment_is_written_under_the_carrier_by_its_id(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_post_fiber_segment(DEN_SLC))
    assert store.items[-1] == {
        "PK": {"S": "carriers/1"}, "SK": {"S": "fiber-segments/4"},
        "a_municipality": {"S": "Denver"}, "a_state": {"S": "CO"},
        "z_municipality": {"S": "Salt Lake City"}, "z_state": {"S": "UT"},
        "submarine": {"BOOL": False},
    }


def test_the_added_fiber_segment_is_then_listed_last(
    answer: Handler, served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_post_fiber_segment(DEN_SLC))
    assert served(_get_fiber_segments())[-1] == {"id": 4, **DEN_SLC}


@pytest.fixture(name="fiber_segment_request")
def fiber_segment_request_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(_post_fiber_segment(DEN_SLC))
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
    assert answer(_post_fiber_segment(DEN_SLC, "3"))["statusCode"] == 404


def test_adding_a_fiber_segment_to_an_unknown_carrier_names_the_error(served: Served) -> None:
    assert served(_post_fiber_segment(DEN_SLC, "3"))["error"] == "No such carrier"


def test_adding_a_fiber_segment_to_an_unknown_carrier_writes_nothing(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_post_fiber_segment(DEN_SLC, "3"))
    assert store.items == []


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_adding_a_fiber_segment_to_an_id_that_is_not_a_number_answers_404(
    answer: Handler, carrier: str
) -> None:
    assert answer(_post_fiber_segment(DEN_SLC, carrier))["statusCode"] == 404


UNSPANNED = [
    {},
    {**DEN_SLC, "id": 9},
    {**DEN_SLC, "submarine": "false"},
    {**DEN_SLC, "submarine": 0},
    {**DEN_SLC, "a_municipality": ""},
    {**DEN_SLC, "z_municipality": ""},
    {**DEN_SLC, "a_state": None},
    {**DEN_SLC, "z_state": 1},
    dict(list(DEN_SLC.items())[:4]),
    [DEN_SLC],
]


@pytest.mark.parametrize("body", UNSPANNED)
def test_a_fiber_segment_that_is_not_exactly_a_span_answers_400(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], body: Any
) -> None:
    store.items.extend(carriers)
    assert answer(_post_fiber_segment(body))["statusCode"] == 400


def test_a_fiber_segment_that_is_not_json_answers_400(answer: Handler) -> None:
    event = {**_post_fiber_segment({}), "body": "{"}
    assert answer(event)["statusCode"] == 400


def test_a_refused_fiber_segment_names_what_is_expected(served: Served) -> None:
    assert served(_post_fiber_segment({}))["error"] == FIBER_SEGMENT_BODY


def test_a_refused_fiber_segment_changes_nothing(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_post_fiber_segment({}))
    assert (store.updates, len(store.items)) == ([], len(carriers))


def test_a_store_that_refuses_the_fiber_segment_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_post_fiber_segment(DEN_SLC))["statusCode"] == 500


def test_a_store_that_refuses_the_fiber_segment_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_post_fiber_segment(DEN_SLC))["error"] == "Failed to add the fiber segment"


FIBER_SEGMENT = "/carriers/{carrier}/fiber-segments/{fiber-segment}"


def _get_fiber_segment(carrier: str = "1", fiber_segment: str = "3") -> Dict[str, Any]:
    event = {"resource": FIBER_SEGMENT, "httpMethod": "GET"}
    return {**event, "pathParameters": {"carrier": carrier, "fiber-segment": fiber_segment}}


def test_a_stored_fiber_segment_answers_200(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_get_fiber_segment())["statusCode"] == 200


def test_a_stored_fiber_segment_answers_by_its_id_and_the_span_it_covers(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_get_fiber_segment()) == NYC_AMS


@pytest.fixture(name="fiber_segment_gets")
def fiber_segment_gets_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    store.items.extend(carriers)
    answer(_get_fiber_segment())
    return [dict(one) for one in store.gets]


def test_a_fiber_segment_is_read_after_its_carrier(
    fiber_segment_gets: List[Dict[str, Any]]
) -> None:
    assert [one["Key"] for one in fiber_segment_gets] == [
        {"PK": {"S": "carriers"}, "SK": {"S": "1"}},
        {"PK": {"S": "carriers/1"}, "SK": {"S": "fiber-segments/3"}},
    ]


def test_a_fiber_segment_is_read_from_the_table_the_environment_names(
    fiber_segment_gets: List[Dict[str, Any]]
) -> None:
    assert [one["TableName"] for one in fiber_segment_gets] == ["store", "store"]


def test_a_fiber_segment_of_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(_get_fiber_segment("3"))["statusCode"] == 404


def test_a_fiber_segment_of_an_unknown_carrier_names_the_carrier(served: Served) -> None:
    assert served(_get_fiber_segment("3"))["error"] == "No such carrier"


def test_a_fiber_segment_of_an_unknown_carrier_is_not_looked_for(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_get_fiber_segment("3"))
    assert len(store.gets) == 1


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_a_fiber_segment_of_an_id_that_is_not_a_number_answers_404(
    answer: Handler, carrier: str
) -> None:
    assert answer(_get_fiber_segment(carrier))["statusCode"] == 404


def test_an_unknown_fiber_segment_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_get_fiber_segment("1", "2"))["statusCode"] == 404


def test_an_unknown_fiber_segment_names_the_fiber_segment(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_get_fiber_segment("1", "2"))["error"] == "No such fiber segment"


@pytest.mark.parametrize("fiber_segment", ["#", "", "3/", "-1"])
def test_a_fiber_segment_id_that_is_not_a_number_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], fiber_segment: str
) -> None:
    store.items.extend(carriers)
    assert answer(_get_fiber_segment("1", fiber_segment))["statusCode"] == 404


@pytest.mark.parametrize("fiber_segment", ["#", "", "3/", "-1"])
def test_a_fiber_segment_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, fiber_segment: str
) -> None:
    answer(_get_fiber_segment("1", fiber_segment))
    assert store.gets == []


def test_a_store_that_refuses_the_fiber_segment_read_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_get_fiber_segment())["statusCode"] == 500


def test_a_store_that_refuses_the_fiber_segment_read_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_fiber_segment())["error"] == "Failed to read the fiber segment"


def _put_fiber_segment(body: Any, carrier: str = "1", fiber_segment: str = "3") -> Dict[str, Any]:
    event = {"resource": FIBER_SEGMENT, "httpMethod": "PUT", "body": json.dumps(body)}
    return {**event, "pathParameters": {"carrier": carrier, "fiber-segment": fiber_segment}}


def test_a_stored_fiber_segment_is_corrected_with_200(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_put_fiber_segment(DEN_SLC))["statusCode"] == 200


def test_a_corrected_fiber_segment_answers_by_its_id_and_new_span(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_put_fiber_segment(DEN_SLC)) == {"id": 3, **DEN_SLC}


def test_a_fiber_segment_corrected_to_a_submarine_span_answers_as_submarine_with_no_states(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_put_fiber_segment(LON_PAR, "1", "1")) == {"id": 1, **LON_PAR}


def test_a_corrected_fiber_segment_is_then_served_at_its_own_url(
    answer: Handler, served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_put_fiber_segment(DEN_SLC))
    assert served(_get_fiber_segment()) == {"id": 3, **DEN_SLC}


def test_a_correction_leaves_the_carrier_s_other_fiber_segments_as_they_were(
    answer: Handler, served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_put_fiber_segment(DEN_SLC))
    assert served(_get_fiber_segments()) == [DEN_ORD, {"id": 3, **DEN_SLC}]


def test_a_correction_leaves_the_carrier_s_next_fiber_segment_where_it_was(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], lumen: Dict[str, Any]
) -> None:
    store.items.extend(carriers)
    answer(_put_fiber_segment(DEN_SLC))
    assert lumen["next_fiber_segment"] == {"N": "4"}


@pytest.fixture(name="span_correction")
def span_correction_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(_put_fiber_segment(DEN_SLC))
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
    answer(_put_fiber_segment(DEN_SLC))
    assert [one["Key"] for one in store.gets] == [{"PK": {"S": "carriers"}, "SK": {"S": "1"}}]


def test_correcting_a_fiber_segment_of_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(_put_fiber_segment(DEN_SLC, "3"))["statusCode"] == 404


def test_correcting_a_fiber_segment_of_an_unknown_carrier_names_the_carrier(
    served: Served
) -> None:
    assert served(_put_fiber_segment(DEN_SLC, "3"))["error"] == "No such carrier"


def test_correcting_a_fiber_segment_of_an_unknown_carrier_writes_nothing(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_put_fiber_segment(DEN_SLC, "3"))
    assert store.puts == []


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_correcting_a_fiber_segment_of_an_id_that_is_not_a_number_answers_404(
    answer: Handler, carrier: str
) -> None:
    assert answer(_put_fiber_segment(DEN_SLC, carrier))["statusCode"] == 404


def test_correcting_an_unknown_fiber_segment_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_put_fiber_segment(DEN_SLC, "1", "2"))["statusCode"] == 404


def test_correcting_an_unknown_fiber_segment_names_the_fiber_segment(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_put_fiber_segment(DEN_SLC, "1", "2"))["error"] == "No such fiber segment"


def test_correcting_an_unknown_fiber_segment_adds_none(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_put_fiber_segment(DEN_SLC, "1", "2"))
    assert len(store.items) == len(carriers)


@pytest.mark.parametrize("fiber_segment", ["#", "", "3/", "-1"])
def test_correcting_a_fiber_segment_id_that_is_not_a_number_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], fiber_segment: str
) -> None:
    store.items.extend(carriers)
    assert answer(_put_fiber_segment(DEN_SLC, "1", fiber_segment))["statusCode"] == 404


@pytest.mark.parametrize("fiber_segment", ["#", "", "3/", "-1"])
def test_correcting_a_fiber_segment_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, fiber_segment: str
) -> None:
    answer(_put_fiber_segment(DEN_SLC, "1", fiber_segment))
    assert (store.gets, store.puts) == ([], [])


@pytest.mark.parametrize("body", UNSPANNED)
def test_a_span_correction_that_is_not_exactly_a_span_answers_400(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], body: Any
) -> None:
    store.items.extend(carriers)
    assert answer(_put_fiber_segment(body))["statusCode"] == 400


def test_a_span_correction_that_is_not_json_answers_400(answer: Handler) -> None:
    event = {**_put_fiber_segment({}), "body": "{"}
    assert answer(event)["statusCode"] == 400


def test_a_refused_span_correction_names_what_is_expected(served: Served) -> None:
    assert served(_put_fiber_segment({}))["error"] == FIBER_SEGMENT_BODY


def test_a_refused_span_correction_changes_nothing(
    answer: Handler, served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_put_fiber_segment({}))
    assert (store.puts, served(_get_fiber_segment())) == ([], NYC_AMS)


def test_a_store_that_refuses_the_span_correction_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_put_fiber_segment(DEN_SLC))["statusCode"] == 500


def test_a_store_that_refuses_the_span_correction_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_put_fiber_segment(DEN_SLC))["error"] == "Failed to update the fiber segment"
