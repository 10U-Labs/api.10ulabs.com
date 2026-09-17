import json
from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler
from pops import CHICAGO, DENVER, BOISE, AMSTERDAM, POP_BODY, MISPLACED, put_pop

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/correct_pop"


def test_a_stored_pop_is_corrected_with_200(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(put_pop(BOISE))["statusCode"] == 200


def test_a_corrected_pop_answers_by_its_id_and_new_place(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(put_pop(BOISE)) == {"id": 3, **BOISE}


def test_a_pop_corrected_to_outside_a_country_with_states_answers_with_no_state(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(put_pop(AMSTERDAM))["state"] == ""


def test_a_corrected_pop_is_then_served_at_its_own_url(
    answer: Handler, pop_read: Callable[[], Dict[str, Any]], store: SimpleNamespace,
    carriers: List[Dict[str, Any]],
) -> None:
    store.items.extend(carriers)
    answer(put_pop(BOISE))
    assert json.loads(pop_read()["body"]) == {"id": 3, **BOISE}


def test_a_correction_leaves_the_carrier_s_other_pops_as_they_were(
    answer: Handler, pops_listed: Callable[[], Any], store: SimpleNamespace,
    carriers: List[Dict[str, Any]],
) -> None:
    store.items.extend(carriers)
    answer(put_pop(BOISE))
    assert pops_listed() == [DENVER, {"id": 3, **BOISE}]


def test_a_correction_leaves_the_carrier_s_next_pop_where_it_was(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], lumen: Dict[str, Any]
) -> None:
    store.items.extend(carriers)
    answer(put_pop(BOISE))
    assert lumen["next_pop"] == {"N": "4"}


@pytest.fixture(name="correction")
def correction_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(put_pop(BOISE))
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
    answer(put_pop(BOISE))
    assert [one["Key"] for one in store.gets] == [{"PK": {"S": "carriers"}, "SK": {"S": "1"}}]


def test_correcting_a_pop_of_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(put_pop(BOISE, "3"))["statusCode"] == 404


def test_correcting_a_pop_of_an_unknown_carrier_names_the_carrier(served: Served) -> None:
    assert served(put_pop(BOISE, "3"))["error"] == "No such carrier"


def test_correcting_a_pop_of_an_unknown_carrier_writes_nothing(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(put_pop(BOISE, "3"))
    assert store.puts == []


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_correcting_a_pop_of_an_id_that_is_not_a_number_answers_404(
    answer: Handler, carrier: str
) -> None:
    assert answer(put_pop(BOISE, carrier))["statusCode"] == 404


def test_correcting_an_unknown_pop_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(put_pop(BOISE, "1", "2"))["statusCode"] == 404


def test_correcting_an_unknown_pop_names_the_pop(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(put_pop(BOISE, "1", "2"))["error"] == "No such pop"


def test_correcting_an_unknown_pop_adds_none(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(put_pop(BOISE, "1", "2"))
    assert len(store.items) == len(carriers)


@pytest.mark.parametrize("pop", ["#", "", "3/", "-1"])
def test_correcting_a_pop_id_that_is_not_a_number_answers_404(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], pop: str
) -> None:
    store.items.extend(carriers)
    assert answer(put_pop(BOISE, "1", pop))["statusCode"] == 404


@pytest.mark.parametrize("pop", ["#", "", "3/", "-1"])
def test_correcting_a_pop_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, pop: str
) -> None:
    answer(put_pop(BOISE, "1", pop))
    assert (store.gets, store.puts) == ([], [])


@pytest.mark.parametrize("body", MISPLACED)
def test_a_correction_that_is_not_exactly_a_located_municipality_answers_400(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], body: Any
) -> None:
    store.items.extend(carriers)
    assert answer(put_pop(body))["statusCode"] == 400


def test_a_correction_that_is_not_json_answers_400(answer: Handler) -> None:
    event = {**put_pop({}), "body": "{"}
    assert answer(event)["statusCode"] == 400


def test_a_refused_correction_names_what_is_expected(served: Served) -> None:
    assert served(put_pop({}))["error"] == POP_BODY


def test_a_refused_correction_changes_nothing(
    pop_read: Callable[[], Dict[str, Any]], served: Served, store: SimpleNamespace,
    carriers: List[Dict[str, Any]],
) -> None:
    store.items.extend(carriers)
    refusal = served(put_pop({}))["error"]
    assert (refusal, store.puts, json.loads(pop_read()["body"])) == (POP_BODY, [], CHICAGO)


def test_a_store_that_refuses_the_correction_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(put_pop(BOISE))["statusCode"] == 500


def test_a_store_that_refuses_the_correction_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(put_pop(BOISE))["error"] == "Failed to update the pop"


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**put_pop(BOISE), "httpMethod": "POST"})["statusCode"] == 404


def test_another_resource_answers_404(answer: Handler) -> None:
    assert answer({**put_pop(BOISE), "resource": "/carriers/{id}"})["statusCode"] == 404
