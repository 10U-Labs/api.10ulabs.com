from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler
from pops import AMSTERDAM, BOISE, BOISE_ITEM, MISPLACED, POPS_BODY, put_pops

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/replace_pops"
REPLACED = [{"id": 4, **BOISE}, {"id": 5, **AMSTERDAM}]


@pytest.fixture(name="replacement")
def replacement_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    return answer(put_pops([BOISE, AMSTERDAM]))


def test_a_carrier_s_pops_are_replaced_with_200(replacement: Dict[str, Any]) -> None:
    assert replacement["statusCode"] == 200


def test_a_replacement_answers_the_new_pops_under_fresh_ids(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(put_pops([BOISE, AMSTERDAM])) == REPLACED


@pytest.mark.usefixtures("replacement")
def test_the_new_pops_are_then_listed_in_place_of_the_old(pops_listed: Callable[[], Any]) -> None:
    assert pops_listed() == REPLACED


@pytest.mark.usefixtures("replacement")
def test_a_replaced_pop_is_no_longer_served(pop_read: Callable[[], Dict[str, Any]]) -> None:
    assert pop_read()["statusCode"] == 404


@pytest.mark.usefixtures("replacement")
def test_the_carrier_s_next_pop_moves_past_the_ids_it_gave(lumen: Dict[str, Any]) -> None:
    assert lumen["next_pop"] == {"N": "6"}


@pytest.mark.usefixtures("replacement")
def test_a_replacement_leaves_the_carrier_s_fiber_segments_as_they_were(
    store: SimpleNamespace,
) -> None:
    under = [item["SK"]["S"] for item in store.items if item["PK"] == {"S": "carriers/1"}]
    assert [key for key in under if key.startswith("fiber-segments/")] == [
        "fiber-segments/3", "fiber-segments/1",
    ]


@pytest.mark.usefixtures("replacement")
def test_a_new_pop_is_written_under_the_carrier_by_its_id(store: SimpleNamespace) -> None:
    assert store.items[-2] == BOISE_ITEM


@pytest.mark.usefixtures("replacement")
def test_a_replacement_writes_to_the_table_the_environment_names(store: SimpleNamespace) -> None:
    assert {table for batch in store.batches for table in batch["RequestItems"]} == {"store"}


@pytest.mark.usefixtures("replacement")
def test_a_replacement_takes_its_ids_from_the_carrier_s_own_item(store: SimpleNamespace) -> None:
    assert [one["Key"] for one in store.updates] == [{"PK": {"S": "carriers"}, "SK": {"S": "1"}}]


@pytest.mark.usefixtures("replacement")
def test_a_replacement_takes_one_id_for_each_pop_in_one_update(store: SimpleNamespace) -> None:
    assert store.updates[0]["ExpressionAttributeValues"][":count"] == {"N": "2"}


@pytest.mark.usefixtures("replacement")
def test_taking_the_ids_requires_the_carrier_to_exist_in_the_store(
    store: SimpleNamespace,
) -> None:
    assert store.updates[0]["ConditionExpression"] == "attribute_exists(PK)"


@pytest.mark.usefixtures("replacement")
def test_a_replacement_invalidates_the_carrier_s_pops_once(distribution: SimpleNamespace) -> None:
    assert distribution.invalidated == [["/carriers/1/pops", "/carriers/1/pops/*"]]


def test_a_list_longer_than_a_batch_is_stored_whole(
    answer: Handler, pops_listed: Callable[[], Any], store: SimpleNamespace,
    carriers: List[Dict[str, Any]],
) -> None:
    store.items.extend(carriers)
    answer(put_pops([{**BOISE, "latitude": 40 + index} for index in range(30)]))
    assert len(pops_listed()) == 30


@pytest.fixture(name="emptied")
def emptied_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    return answer(put_pops([]))


def test_an_empty_list_answers_an_empty_list(emptied: Dict[str, Any]) -> None:
    assert emptied["body"] == "[]"


@pytest.mark.usefixtures("emptied")
def test_an_empty_list_removes_every_pop_of_the_carrier(pops_listed: Callable[[], Any]) -> None:
    assert pops_listed() == []


@pytest.mark.usefixtures("emptied")
def test_an_empty_list_leaves_the_carrier_s_next_pop_where_it_was(lumen: Dict[str, Any]) -> None:
    assert lumen["next_pop"] == {"N": "4"}


def test_replacing_the_pops_of_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(put_pops([BOISE], "3"))["statusCode"] == 404


def test_replacing_the_pops_of_an_unknown_carrier_names_the_error(served: Served) -> None:
    assert served(put_pops([BOISE], "3"))["error"] == "No such carrier"


def test_replacing_the_pops_of_an_unknown_carrier_writes_nothing(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(put_pops([BOISE], "3"))
    assert (store.items, store.batches) == ([], [])


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_replacing_the_pops_of_an_id_that_is_not_a_number_answers_404(
    answer: Handler, carrier: str
) -> None:
    assert answer(put_pops([BOISE], carrier))["statusCode"] == 404


@pytest.mark.parametrize("body", [{}, BOISE, None, "Boise", *[[BOISE, one] for one in MISPLACED]])
def test_a_body_that_is_not_a_list_of_located_municipalities_answers_400(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], body: Any
) -> None:
    store.items.extend(carriers)
    assert answer(put_pops(body))["statusCode"] == 400


def test_a_list_of_pops_that_is_not_json_answers_400(answer: Handler) -> None:
    event = {**put_pops([]), "body": "["}
    assert answer(event)["statusCode"] == 400


def test_a_refused_list_of_pops_names_what_is_expected(served: Served) -> None:
    assert served(put_pops({}))["error"] == POPS_BODY


def test_a_refused_list_of_pops_changes_nothing(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(put_pops([BOISE, {}]))
    assert (store.updates, store.batches, len(store.items)) == ([], [], len(carriers))


def test_a_store_that_refuses_the_pops_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(put_pops([BOISE]))["statusCode"] == 500


def test_a_store_that_refuses_the_pops_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(put_pops([BOISE]))["error"] == "Failed to replace the pops"


def test_another_verb_on_the_pops_answers_404(answer: Handler) -> None:
    assert answer({**put_pops([BOISE]), "httpMethod": "DELETE"})["statusCode"] == 404


def test_another_resource_than_the_pops_answers_404(answer: Handler) -> None:
    assert answer({**put_pops([BOISE]), "resource": "/carriers/{id}"})["statusCode"] == 404
