import json
from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
POPS = "/carriers/{carrier_id}/pops"
CHICAGO = {"id": 3, "municipality": "Chicago", "state": "IL", "country": "US",
           "latitude": 41.8781, "longitude": -87.6298}
DENVER = {"id": 1, "municipality": "Denver", "state": "CO", "country": "US",
          "latitude": 39.7392, "longitude": -104.9903}


def _get_pops(carrier: str = "1") -> Dict[str, Any]:
    return {"resource": POPS, "httpMethod": "GET", "pathParameters": {"carrier_id": carrier}}


def test_the_pops_of_a_stored_carrier_answer_200(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_get_pops())["statusCode"] == 200


def test_the_pops_answer_as_rows_in_id_order(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_get_pops()) == [DENVER, CHICAGO]


def test_a_carrier_without_pops_answers_none(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_get_pops("2")) == []


@pytest.fixture(name="pops_query")
def pops_query_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(_get_pops())
    return dict(store.queries[-1])


def test_the_pops_are_read_from_under_the_carrier(pops_query: Dict[str, Any]) -> None:
    assert pops_query["ExpressionAttributeValues"] == {
        ":pk": {"S": "carriers/1"}, ":prefix": {"S": "pops/"},
    }


def test_the_pops_are_read_from_the_table_the_environment_names(
    pops_query: Dict[str, Any]
) -> None:
    assert pops_query["TableName"] == "store"


def test_the_pops_of_an_unknown_carrier_answer_404(answer: Handler) -> None:
    assert answer(_get_pops("3"))["statusCode"] == 404


def test_the_pops_of_an_unknown_carrier_name_the_error(served: Served) -> None:
    assert served(_get_pops("3"))["error"] == "No such carrier"


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_the_pops_of_an_id_that_is_not_a_number_answer_404(answer: Handler, carrier: str) -> None:
    assert answer(_get_pops(carrier))["statusCode"] == 404


def test_a_store_that_refuses_the_pops_answers_500(answer: Handler, store: SimpleNamespace) -> None:
    store.failing = True
    assert answer(_get_pops())["statusCode"] == 500


def test_a_store_that_refuses_the_pops_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_pops())["error"] == "Failed to read the pops"


BOISE = {"municipality": "Boise", "state": "ID", "country": "US",
         "latitude": 43.615, "longitude": -116.2023}
AMSTERDAM = {"municipality": "Amsterdam", "state": "", "country": "Netherlands",
             "latitude": 52.3731, "longitude": 4.8925}
POP_BODY = 'The body must be exactly {"municipality", "state", "country", "latitude", "longitude"}'


def _post_pop(body: Any, carrier: str = "1") -> Dict[str, Any]:
    event = {"resource": POPS, "httpMethod": "POST", "body": json.dumps(body)}
    return {**event, "pathParameters": {"carrier_id": carrier}}


def test_a_pop_is_added_with_201(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_post_pop(BOISE))["statusCode"] == 201


def test_a_pop_outside_a_country_with_states_is_added_with_201(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_post_pop(AMSTERDAM))["statusCode"] == 201


def test_a_pop_outside_a_country_with_states_answers_with_no_state(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_post_pop(AMSTERDAM))["state"] == ""


def test_the_added_pop_answers_with_the_id_the_carrier_holds_next(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_post_pop(BOISE)) == {"id": 4, **BOISE}


def test_the_added_pop_is_located_under_the_carrier_s_pops(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    headers = answer(_post_pop(BOISE))["headers"]
    assert headers["Location"] == "/carriers/1/pops/4"


def test_the_carrier_s_next_pop_moves_past_the_id_it_gave(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], lumen: Dict[str, Any]
) -> None:
    store.items.extend(carriers)
    answer(_post_pop(BOISE))
    assert lumen["next_pop"] == {"N": "5"}


def test_a_pop_id_is_never_reused(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    pops = (BOISE, {**BOISE, "municipality": "Reno"})
    assert [served(_post_pop(pop, "2"))["id"] for pop in pops] == [1, 2]


def test_the_pop_is_written_under_the_carrier_by_its_id(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_post_pop(BOISE))
    assert store.items[-1] == {
        "PK": {"S": "carriers/1"}, "SK": {"S": "pops/4"}, "municipality": {"S": "Boise"},
        "state": {"S": "ID"}, "country": {"S": "US"},
        "latitude": {"N": "43.615"}, "longitude": {"N": "-116.2023"},
    }


def test_the_added_pop_is_then_listed_last(
    answer: Handler, served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_post_pop(BOISE))
    assert served(_get_pops())[-1] == {"id": 4, **BOISE}


@pytest.fixture(name="pop_request")
def pop_request_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(_post_pop(BOISE))
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


def test_adding_a_pop_to_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(_post_pop(BOISE, "3"))["statusCode"] == 404


def test_adding_a_pop_to_an_unknown_carrier_names_the_error(served: Served) -> None:
    assert served(_post_pop(BOISE, "3"))["error"] == "No such carrier"


def test_adding_a_pop_to_an_unknown_carrier_writes_nothing(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_post_pop(BOISE, "3"))
    assert store.items == []


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_adding_a_pop_to_an_id_that_is_not_a_number_answers_404(
    answer: Handler, carrier: str
) -> None:
    assert answer(_post_pop(BOISE, carrier))["statusCode"] == 404


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
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], body: Any
) -> None:
    store.items.extend(carriers)
    assert answer(_post_pop(body))["statusCode"] == 400


def test_a_pop_that_is_not_json_answers_400(answer: Handler) -> None:
    event = {**_post_pop({}), "body": "{"}
    assert answer(event)["statusCode"] == 400


def test_a_refused_pop_names_what_is_expected(served: Served) -> None:
    assert served(_post_pop({}))["error"] == POP_BODY


def test_a_refused_pop_changes_nothing(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_post_pop({}))
    assert (store.updates, len(store.items)) == ([], len(carriers))


def test_a_store_that_refuses_the_pop_answers_500(answer: Handler, store: SimpleNamespace) -> None:
    store.failing = True
    assert answer(_post_pop(BOISE))["statusCode"] == 500


def test_a_store_that_refuses_the_pop_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_post_pop(BOISE))["error"] == "Failed to add the pop"


POP = "/carriers/{carrier_id}/pops/{id}"


def _get_pop(carrier: str = "1", pop: str = "3") -> Dict[str, Any]:
    event = {"resource": POP, "httpMethod": "GET"}
    return {**event, "pathParameters": {"carrier_id": carrier, "id": pop}}


def test_a_stored_pop_answers_200(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_get_pop())["statusCode"] == 200


def test_a_stored_pop_answers_by_its_id_and_where_it_is(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_get_pop()) == CHICAGO


@pytest.fixture(name="pop_gets")
def pop_gets_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    store.items.extend(carriers)
    answer(_get_pop())
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


def test_a_pop_of_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(_get_pop("3"))["statusCode"] == 404


def test_a_pop_of_an_unknown_carrier_names_the_carrier(served: Served) -> None:
    assert served(_get_pop("3"))["error"] == "No such carrier"


def test_a_pop_of_an_unknown_carrier_is_not_looked_for(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_get_pop("3"))
    assert len(store.gets) == 1


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_a_pop_of_an_id_that_is_not_a_number_answers_404(answer: Handler, carrier: str) -> None:
    assert answer(_get_pop(carrier))["statusCode"] == 404


def test_an_unknown_pop_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_get_pop("1", "2"))["statusCode"] == 404


def test_an_unknown_pop_names_the_pop(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_get_pop("1", "2"))["error"] == "No such pop"


@pytest.mark.parametrize("pop", ["#", "", "3/", "-1"])
def test_a_pop_id_that_is_not_a_number_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], pop: str
) -> None:
    store.items.extend(carriers)
    assert answer(_get_pop("1", pop))["statusCode"] == 404


@pytest.mark.parametrize("pop", ["#", "", "3/", "-1"])
def test_a_pop_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, pop: str
) -> None:
    answer(_get_pop("1", pop))
    assert store.gets == []


def test_a_store_that_refuses_the_pop_read_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_get_pop())["statusCode"] == 500


def test_a_store_that_refuses_the_pop_read_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_pop())["error"] == "Failed to read the pop"


def _put_pop(body: Any, carrier: str = "1", pop: str = "3") -> Dict[str, Any]:
    event = {"resource": POP, "httpMethod": "PUT", "body": json.dumps(body)}
    return {**event, "pathParameters": {"carrier_id": carrier, "id": pop}}


def test_a_stored_pop_is_corrected_with_200(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_put_pop(BOISE))["statusCode"] == 200


def test_a_corrected_pop_answers_by_its_id_and_new_place(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_put_pop(BOISE)) == {"id": 3, **BOISE}


def test_a_pop_corrected_to_outside_a_country_with_states_answers_with_no_state(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_put_pop(AMSTERDAM))["state"] == ""


def test_a_corrected_pop_is_then_served_at_its_own_url(
    answer: Handler, served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_put_pop(BOISE))
    assert served(_get_pop()) == {"id": 3, **BOISE}


def test_a_correction_leaves_the_carrier_s_other_pops_as_they_were(
    answer: Handler, served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_put_pop(BOISE))
    assert served(_get_pops()) == [DENVER, {"id": 3, **BOISE}]


def test_a_correction_leaves_the_carrier_s_next_pop_where_it_was(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], lumen: Dict[str, Any]
) -> None:
    store.items.extend(carriers)
    answer(_put_pop(BOISE))
    assert lumen["next_pop"] == {"N": "4"}


@pytest.fixture(name="correction")
def correction_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(_put_pop(BOISE))
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
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_put_pop(BOISE))
    assert [one["Key"] for one in store.gets] == [{"PK": {"S": "carriers"}, "SK": {"S": "1"}}]


def test_correcting_a_pop_of_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(_put_pop(BOISE, "3"))["statusCode"] == 404


def test_correcting_a_pop_of_an_unknown_carrier_names_the_carrier(served: Served) -> None:
    assert served(_put_pop(BOISE, "3"))["error"] == "No such carrier"


def test_correcting_a_pop_of_an_unknown_carrier_writes_nothing(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_put_pop(BOISE, "3"))
    assert store.puts == []


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_correcting_a_pop_of_an_id_that_is_not_a_number_answers_404(
    answer: Handler, carrier: str
) -> None:
    assert answer(_put_pop(BOISE, carrier))["statusCode"] == 404


def test_correcting_an_unknown_pop_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_put_pop(BOISE, "1", "2"))["statusCode"] == 404


def test_correcting_an_unknown_pop_names_the_pop(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_put_pop(BOISE, "1", "2"))["error"] == "No such pop"


def test_correcting_an_unknown_pop_adds_none(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_put_pop(BOISE, "1", "2"))
    assert len(store.items) == len(carriers)


@pytest.mark.parametrize("pop", ["#", "", "3/", "-1"])
def test_correcting_a_pop_id_that_is_not_a_number_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], pop: str
) -> None:
    store.items.extend(carriers)
    assert answer(_put_pop(BOISE, "1", pop))["statusCode"] == 404


@pytest.mark.parametrize("pop", ["#", "", "3/", "-1"])
def test_correcting_a_pop_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, pop: str
) -> None:
    answer(_put_pop(BOISE, "1", pop))
    assert (store.gets, store.puts) == ([], [])


@pytest.mark.parametrize("body", MISPLACED)
def test_a_correction_that_is_not_exactly_a_located_municipality_answers_400(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], body: Any
) -> None:
    store.items.extend(carriers)
    assert answer(_put_pop(body))["statusCode"] == 400


def test_a_correction_that_is_not_json_answers_400(answer: Handler) -> None:
    event = {**_put_pop({}), "body": "{"}
    assert answer(event)["statusCode"] == 400


def test_a_refused_correction_names_what_is_expected(served: Served) -> None:
    assert served(_put_pop({}))["error"] == POP_BODY


def test_a_refused_correction_changes_nothing(
    answer: Handler, served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_put_pop({}))
    assert (store.puts, served(_get_pop())) == ([], CHICAGO)


def test_a_store_that_refuses_the_correction_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_put_pop(BOISE))["statusCode"] == 500


def test_a_store_that_refuses_the_correction_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_put_pop(BOISE))["error"] == "Failed to update the pop"


def _delete_pop(carrier: str = "1", pop: str = "3") -> Dict[str, Any]:
    return {**_get_pop(carrier, pop), "httpMethod": "DELETE"}


@pytest.fixture(name="removed")
def removed_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    return answer(_delete_pop())


def test_a_stored_pop_is_removed_with_204(removed: Dict[str, Any]) -> None:
    assert removed["statusCode"] == 204


def test_a_removal_answers_no_content(removed: Dict[str, Any]) -> None:
    assert removed["body"] == ""


@pytest.mark.usefixtures("removed")
def test_a_removed_pop_is_no_longer_listed(served: Served) -> None:
    assert served(_get_pops()) == [DENVER]


@pytest.mark.usefixtures("removed")
def test_a_removed_pop_is_no_longer_served(answer: Handler) -> None:
    assert answer(_get_pop())["statusCode"] == 404


@pytest.mark.usefixtures("removed")
def test_a_removal_leaves_the_carrier_s_next_pop_where_it_was(lumen: Dict[str, Any]) -> None:
    assert lumen["next_pop"] == {"N": "4"}


@pytest.mark.usefixtures("removed")
def test_a_removal_leaves_the_rest_of_the_carrier_as_it_was(store: SimpleNamespace) -> None:
    under = [item["SK"]["S"] for item in store.items if item["PK"] == {"S": "carriers/1"}]
    assert under == ["pops/1", "fiber-segments/3", "fiber-segments/1"]


@pytest.mark.usefixtures("removed")
def test_a_removal_goes_to_the_table_the_environment_names(store: SimpleNamespace) -> None:
    assert [one["TableName"] for one in store.deletes] == ["store"]


@pytest.mark.usefixtures("removed")
def test_a_removal_deletes_the_pop_under_the_carrier_by_its_id(store: SimpleNamespace) -> None:
    assert [one["Key"] for one in store.deletes] == [
        {"PK": {"S": "carriers/1"}, "SK": {"S": "pops/3"}},
    ]


@pytest.mark.usefixtures("removed")
def test_a_removal_requires_the_pop_to_exist_in_the_store(store: SimpleNamespace) -> None:
    assert store.deletes[0]["ConditionExpression"] == "attribute_exists(PK)"


@pytest.mark.usefixtures("removed")
def test_a_removal_reads_the_carrier_first(store: SimpleNamespace) -> None:
    assert [one["Key"] for one in store.gets] == [{"PK": {"S": "carriers"}, "SK": {"S": "1"}}]


def test_removing_a_pop_of_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(_delete_pop("3"))["statusCode"] == 404


def test_removing_a_pop_of_an_unknown_carrier_names_the_carrier(served: Served) -> None:
    assert served(_delete_pop("3"))["error"] == "No such carrier"


def test_removing_a_pop_of_an_unknown_carrier_deletes_nothing(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_delete_pop("3"))
    assert store.deletes == []


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_removing_a_pop_of_an_id_that_is_not_a_number_answers_404(
    answer: Handler, carrier: str
) -> None:
    assert answer(_delete_pop(carrier))["statusCode"] == 404


def test_removing_an_unknown_pop_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_delete_pop("1", "2"))["statusCode"] == 404


def test_removing_an_unknown_pop_names_the_pop(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_delete_pop("1", "2"))["error"] == "No such pop"


def test_removing_an_unknown_pop_removes_nothing(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_delete_pop("1", "2"))
    assert len(store.items) == len(carriers)


@pytest.mark.parametrize("pop", ["#", "", "3/", "-1"])
def test_removing_a_pop_id_that_is_not_a_number_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], pop: str
) -> None:
    store.items.extend(carriers)
    assert answer(_delete_pop("1", pop))["statusCode"] == 404


@pytest.mark.parametrize("pop", ["#", "", "3/", "-1"])
def test_removing_a_pop_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, pop: str
) -> None:
    answer(_delete_pop("1", pop))
    assert (store.gets, store.deletes) == ([], [])


def test_a_store_that_refuses_the_removal_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_delete_pop())["statusCode"] == 500


def test_a_store_that_refuses_the_removal_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_delete_pop())["error"] == "Failed to delete the pop"
