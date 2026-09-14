from types import ModuleType, SimpleNamespace
from typing import Any, Dict, List

import pytest
from harness import answer, get, post, served, stored

POPS = "/carriers/{carrier}/pops"
CHICAGO = {"id": 3, "municipality": "Chicago", "state": "IL", "country": "US",
           "latitude": 41.8781, "longitude": -87.6298}
DENVER = {"id": 1, "municipality": "Denver", "state": "CO", "country": "US",
          "latitude": 39.7392, "longitude": -104.9903}


def _get_pops(carrier: str = "1") -> Dict[str, Any]:
    return {**get(POPS), "pathParameters": {"carrier": carrier}}


def test_the_pops_of_a_stored_carrier_answer_200(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(carriers_handler, _get_pops())["statusCode"] == 200


def test_the_pops_answer_as_rows_in_id_order(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(carriers_handler, _get_pops()) == [DENVER, CHICAGO]


def test_a_carrier_without_pops_answers_none(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(carriers_handler, _get_pops("2")) == []


@pytest.fixture(name="pops_query")
def pops_query_fixture(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(carriers_handler, _get_pops())
    return dict(store.queries[-1])


def test_the_pops_are_read_from_under_the_carrier(pops_query: Dict[str, Any]) -> None:
    assert pops_query["ExpressionAttributeValues"] == {
        ":pk": {"S": "carriers/1"}, ":prefix": {"S": "pops/"},
    }


def test_the_pops_are_read_from_the_table_the_environment_names(
    pops_query: Dict[str, Any]
) -> None:
    assert pops_query["TableName"] == "store"


def test_the_pops_of_an_unknown_carrier_answer_404(carriers_handler: ModuleType) -> None:
    assert answer(carriers_handler, _get_pops("3"))["statusCode"] == 404


def test_the_pops_of_an_unknown_carrier_name_the_error(carriers_handler: ModuleType) -> None:
    assert served(carriers_handler, _get_pops("3"))["error"] == "No such carrier"


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_the_pops_of_an_id_that_is_not_a_number_answer_404(
    carriers_handler: ModuleType, carrier: str
) -> None:
    assert answer(carriers_handler, _get_pops(carrier))["statusCode"] == 404


def test_a_store_that_refuses_the_pops_answers_500(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(carriers_handler, _get_pops())["statusCode"] == 500


def test_a_store_that_refuses_the_pops_names_the_error(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(carriers_handler, _get_pops())["error"] == "Failed to read the pops"


BOISE = {"municipality": "Boise", "state": "ID", "country": "US",
         "latitude": 43.615, "longitude": -116.2023}
AMSTERDAM = {"municipality": "Amsterdam", "state": "", "country": "Netherlands",
             "latitude": 52.3731, "longitude": 4.8925}
POP_BODY = 'The body must be exactly {"municipality", "state", "country", "latitude", "longitude"}'


def _post_pop(body: Any, carrier: str = "1") -> Dict[str, Any]:
    return {**post(body, POPS), "pathParameters": {"carrier": carrier}}


def test_a_pop_is_added_with_201(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(carriers_handler, _post_pop(BOISE))["statusCode"] == 201


def test_a_pop_outside_a_country_with_states_is_added_with_201(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(carriers_handler, _post_pop(AMSTERDAM))["statusCode"] == 201


def test_a_pop_outside_a_country_with_states_answers_with_no_state(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(carriers_handler, _post_pop(AMSTERDAM))["state"] == ""


def test_the_added_pop_answers_with_the_id_the_carrier_holds_next(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(carriers_handler, _post_pop(BOISE)) == {"id": 4, **BOISE}


def test_the_added_pop_is_located_under_the_carrier_s_pops(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    headers = answer(carriers_handler, _post_pop(BOISE))["headers"]
    assert headers["Location"] == "/carriers/1/pops/4"


def test_the_carrier_s_next_pop_moves_past_the_id_it_gave(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, _post_pop(BOISE))
    assert stored(store, "1")["next_pop"] == {"N": "5"}


def test_a_pop_id_is_never_reused(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    pops = (BOISE, {**BOISE, "municipality": "Reno"})
    assert [served(carriers_handler, _post_pop(pop, "2"))["id"] for pop in pops] == [1, 2]


def test_the_pop_is_written_under_the_carrier_by_its_id(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, _post_pop(BOISE))
    assert store.items[-1] == {
        "PK": {"S": "carriers/1"}, "SK": {"S": "pops/4"}, "municipality": {"S": "Boise"},
        "state": {"S": "ID"}, "country": {"S": "US"},
        "latitude": {"N": "43.615"}, "longitude": {"N": "-116.2023"},
    }


def test_the_added_pop_is_then_listed_last(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, _post_pop(BOISE))
    assert served(carriers_handler, _get_pops())[-1] == {"id": 4, **BOISE}


@pytest.fixture(name="pop_request")
def pop_request_fixture(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(carriers_handler, _post_pop(BOISE))
    return dict(store.updates[0])


def test_a_pop_id_is_taken_in_the_table_the_environment_names(
    pop_request: Dict[str, Any]
) -> None:
    assert pop_request["TableName"] == "store"


def test_a_pop_id_is_taken_from_the_carrier_s_own_item(pop_request: Dict[str, Any]) -> None:
    assert pop_request["Key"] == {"PK": {"S": "carriers"}, "SK": {"S": "1"}}


def test_taking_a_pop_id_requires_the_carrier_to_exist_in_the_store(
    pop_request: Dict[str, Any]
) -> None:
    assert pop_request["ConditionExpression"] == "attribute_exists(PK)"


def test_adding_a_pop_to_an_unknown_carrier_answers_404(carriers_handler: ModuleType) -> None:
    assert answer(carriers_handler, _post_pop(BOISE, "3"))["statusCode"] == 404


def test_adding_a_pop_to_an_unknown_carrier_names_the_error(carriers_handler: ModuleType) -> None:
    assert served(carriers_handler, _post_pop(BOISE, "3"))["error"] == "No such carrier"


def test_adding_a_pop_to_an_unknown_carrier_writes_nothing(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    answer(carriers_handler, _post_pop(BOISE, "3"))
    assert store.items == []


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_adding_a_pop_to_an_id_that_is_not_a_number_answers_404(
    carriers_handler: ModuleType, carrier: str
) -> None:
    assert answer(carriers_handler, _post_pop(BOISE, carrier))["statusCode"] == 404


MISPLACED = [
    {},
    {**BOISE, "id": 9},
    {**BOISE, "latitude": "43.615"},
    {**BOISE, "longitude": True},
    {**BOISE, "municipality": ""},
    {**BOISE, "state": None},
    {**BOISE, "country": ""},
    dict(list(BOISE.items())[:4]),
    [BOISE],
]


@pytest.mark.parametrize("body", MISPLACED)
def test_a_pop_that_is_not_exactly_a_located_municipality_answers_400(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]], body: Any
) -> None:
    store.items.extend(carriers)
    assert answer(carriers_handler, _post_pop(body))["statusCode"] == 400


def test_a_pop_that_is_not_json_answers_400(carriers_handler: ModuleType) -> None:
    event = {**_post_pop({}), "body": "{"}
    assert answer(carriers_handler, event)["statusCode"] == 400


def test_a_refused_pop_names_what_is_expected(carriers_handler: ModuleType) -> None:
    assert served(carriers_handler, _post_pop({}))["error"] == POP_BODY


def test_a_refused_pop_changes_nothing(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, _post_pop({}))
    assert (store.updates, len(store.items)) == ([], 6)


def test_a_store_that_refuses_the_pop_answers_500(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(carriers_handler, _post_pop(BOISE))["statusCode"] == 500


def test_a_store_that_refuses_the_pop_names_the_error(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(carriers_handler, _post_pop(BOISE))["error"] == "Failed to add the pop"


POP = "/carriers/{carrier}/pops/{pop}"


def _get_pop(carrier: str = "1", pop: str = "3") -> Dict[str, Any]:
    return {**get(POP), "pathParameters": {"carrier": carrier, "pop": pop}}


def test_a_stored_pop_answers_200(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(carriers_handler, _get_pop())["statusCode"] == 200


def test_a_stored_pop_answers_by_its_id_and_where_it_is(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(carriers_handler, _get_pop()) == CHICAGO


@pytest.fixture(name="pop_gets")
def pop_gets_fixture(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    store.items.extend(carriers)
    answer(carriers_handler, _get_pop())
    return [dict(one) for one in store.gets]


def test_a_pop_is_read_after_its_carrier(pop_gets: List[Dict[str, Any]]) -> None:
    assert [one["Key"] for one in pop_gets] == [
        {"PK": {"S": "carriers"}, "SK": {"S": "1"}},
        {"PK": {"S": "carriers/1"}, "SK": {"S": "pops/3"}},
    ]


def test_a_pop_is_read_from_the_table_the_environment_names(
    pop_gets: List[Dict[str, Any]]
) -> None:
    assert [one["TableName"] for one in pop_gets] == ["store", "store"]


def test_a_pop_of_an_unknown_carrier_answers_404(carriers_handler: ModuleType) -> None:
    assert answer(carriers_handler, _get_pop("3"))["statusCode"] == 404


def test_a_pop_of_an_unknown_carrier_names_the_carrier(carriers_handler: ModuleType) -> None:
    assert served(carriers_handler, _get_pop("3"))["error"] == "No such carrier"


def test_a_pop_of_an_unknown_carrier_is_not_looked_for(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    answer(carriers_handler, _get_pop("3"))
    assert len(store.gets) == 1


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_a_pop_of_an_id_that_is_not_a_number_answers_404(
    carriers_handler: ModuleType, carrier: str
) -> None:
    assert answer(carriers_handler, _get_pop(carrier))["statusCode"] == 404


def test_an_unknown_pop_answers_404(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(carriers_handler, _get_pop("1", "2"))["statusCode"] == 404


def test_an_unknown_pop_names_the_pop(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(carriers_handler, _get_pop("1", "2"))["error"] == "No such pop"


@pytest.mark.parametrize("pop", ["#", "", "3/", "-1"])
def test_a_pop_id_that_is_not_a_number_answers_404(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]],
    pop: str,
) -> None:
    store.items.extend(carriers)
    assert answer(carriers_handler, _get_pop("1", pop))["statusCode"] == 404


@pytest.mark.parametrize("pop", ["#", "", "3/", "-1"])
def test_a_pop_id_that_is_not_a_number_asks_the_store_nothing(
    carriers_handler: ModuleType, store: SimpleNamespace, pop: str
) -> None:
    answer(carriers_handler, _get_pop("1", pop))
    assert store.gets == []


def test_a_store_that_refuses_the_pop_read_answers_500(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(carriers_handler, _get_pop())["statusCode"] == 500


def test_a_store_that_refuses_the_pop_read_names_the_error(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(carriers_handler, _get_pop())["error"] == "Failed to read the pop"


def _put_pop(body: Any, carrier: str = "1", pop: str = "3") -> Dict[str, Any]:
    event = {**post(body, POP), "httpMethod": "PUT"}
    return {**event, "pathParameters": {"carrier": carrier, "pop": pop}}


def test_a_stored_pop_is_corrected_with_200(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(carriers_handler, _put_pop(BOISE))["statusCode"] == 200


def test_a_corrected_pop_answers_by_its_id_and_new_place(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(carriers_handler, _put_pop(BOISE)) == {"id": 3, **BOISE}


def test_a_pop_corrected_to_outside_a_country_with_states_answers_with_no_state(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(carriers_handler, _put_pop(AMSTERDAM))["state"] == ""


def test_a_corrected_pop_is_then_served_at_its_own_url(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, _put_pop(BOISE))
    assert served(carriers_handler, _get_pop()) == {"id": 3, **BOISE}


def test_a_correction_leaves_the_carrier_s_other_pops_as_they_were(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, _put_pop(BOISE))
    assert served(carriers_handler, _get_pops()) == [DENVER, {"id": 3, **BOISE}]


def test_a_correction_leaves_the_carrier_s_next_pop_where_it_was(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, _put_pop(BOISE))
    assert stored(store, "1")["next_pop"] == {"N": "4"}


@pytest.fixture(name="correction")
def correction_fixture(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(carriers_handler, _put_pop(BOISE))
    return dict(store.puts[0])


def test_a_correction_goes_to_the_table_the_environment_names(
    correction: Dict[str, Any]
) -> None:
    assert correction["TableName"] == "store"


def test_a_correction_rewrites_the_pop_under_the_carrier_by_its_id(
    correction: Dict[str, Any]
) -> None:
    assert correction["Item"] == {
        "PK": {"S": "carriers/1"}, "SK": {"S": "pops/3"}, "municipality": {"S": "Boise"},
        "state": {"S": "ID"}, "country": {"S": "US"},
        "latitude": {"N": "43.615"}, "longitude": {"N": "-116.2023"},
    }


def test_a_correction_requires_the_pop_to_exist_in_the_store(correction: Dict[str, Any]) -> None:
    assert correction["ConditionExpression"] == "attribute_exists(PK)"


def test_a_correction_reads_the_carrier_first(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, _put_pop(BOISE))
    assert [one["Key"] for one in store.gets] == [{"PK": {"S": "carriers"}, "SK": {"S": "1"}}]


def test_correcting_a_pop_of_an_unknown_carrier_answers_404(carriers_handler: ModuleType) -> None:
    assert answer(carriers_handler, _put_pop(BOISE, "3"))["statusCode"] == 404


def test_correcting_a_pop_of_an_unknown_carrier_names_the_carrier(
    carriers_handler: ModuleType
) -> None:
    assert served(carriers_handler, _put_pop(BOISE, "3"))["error"] == "No such carrier"


def test_correcting_a_pop_of_an_unknown_carrier_writes_nothing(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    answer(carriers_handler, _put_pop(BOISE, "3"))
    assert store.puts == []


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_correcting_a_pop_of_an_id_that_is_not_a_number_answers_404(
    carriers_handler: ModuleType, carrier: str
) -> None:
    assert answer(carriers_handler, _put_pop(BOISE, carrier))["statusCode"] == 404


def test_correcting_an_unknown_pop_answers_404(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(carriers_handler, _put_pop(BOISE, "1", "2"))["statusCode"] == 404


def test_correcting_an_unknown_pop_names_the_pop(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(carriers_handler, _put_pop(BOISE, "1", "2"))["error"] == "No such pop"


def test_correcting_an_unknown_pop_adds_none(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, _put_pop(BOISE, "1", "2"))
    assert len(store.items) == 6


@pytest.mark.parametrize("pop", ["#", "", "3/", "-1"])
def test_correcting_a_pop_id_that_is_not_a_number_answers_404(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]],
    pop: str,
) -> None:
    store.items.extend(carriers)
    assert answer(carriers_handler, _put_pop(BOISE, "1", pop))["statusCode"] == 404


@pytest.mark.parametrize("pop", ["#", "", "3/", "-1"])
def test_correcting_a_pop_id_that_is_not_a_number_asks_the_store_nothing(
    carriers_handler: ModuleType, store: SimpleNamespace, pop: str
) -> None:
    answer(carriers_handler, _put_pop(BOISE, "1", pop))
    assert (store.gets, store.puts) == ([], [])


@pytest.mark.parametrize("body", MISPLACED)
def test_a_correction_that_is_not_exactly_a_located_municipality_answers_400(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]], body: Any
) -> None:
    store.items.extend(carriers)
    assert answer(carriers_handler, _put_pop(body))["statusCode"] == 400


def test_a_correction_that_is_not_json_answers_400(carriers_handler: ModuleType) -> None:
    event = {**_put_pop({}), "body": "{"}
    assert answer(carriers_handler, event)["statusCode"] == 400


def test_a_refused_correction_names_what_is_expected(carriers_handler: ModuleType) -> None:
    assert served(carriers_handler, _put_pop({}))["error"] == POP_BODY


def test_a_refused_correction_changes_nothing(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(carriers_handler, _put_pop({}))
    assert (store.puts, served(carriers_handler, _get_pop())) == ([], CHICAGO)


def test_a_store_that_refuses_the_correction_answers_500(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(carriers_handler, _put_pop(BOISE))["statusCode"] == 500


def test_a_store_that_refuses_the_correction_names_the_error(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(carriers_handler, _put_pop(BOISE))["error"] == "Failed to update the pop"
