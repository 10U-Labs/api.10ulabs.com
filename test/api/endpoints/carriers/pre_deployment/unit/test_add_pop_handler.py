from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler
from pops import BOISE, AMSTERDAM, POP_BODY, MISPLACED, post_pop

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/add_pop"


def test_a_pop_is_added_with_201(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(post_pop(BOISE))["statusCode"] == 201


def test_a_pop_outside_a_country_with_states_is_added_with_201(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(post_pop(AMSTERDAM))["statusCode"] == 201


def test_a_pop_outside_a_country_with_states_answers_with_no_state(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(post_pop(AMSTERDAM))["state"] == ""


def test_the_added_pop_answers_with_the_id_the_carrier_holds_next(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(post_pop(BOISE)) == {"id": 4, **BOISE}


def test_the_added_pop_is_located_under_the_carrier_s_pops(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    headers = answer(post_pop(BOISE))["headers"]
    assert headers["Location"] == "/carriers/1/pops/4"


def test_the_carrier_s_next_pop_moves_past_the_id_it_gave(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], lumen: Dict[str, Any]
) -> None:
    store.items.extend(carriers)
    answer(post_pop(BOISE))
    assert lumen["next_pop"] == {"N": "5"}


def test_a_pop_id_is_never_reused(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    pops = (BOISE, {**BOISE, "municipality": "Reno"})
    assert [served(post_pop(pop, "2"))["id"] for pop in pops] == [1, 2]


def test_the_pop_is_written_under_the_carrier_by_its_id(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(post_pop(BOISE))
    assert store.items[-1] == {
        "PK": {"S": "carriers/1"}, "SK": {"S": "pops/4"}, "municipality": {"S": "Boise"},
        "state": {"S": "ID"}, "country": {"S": "US"},
        "latitude": {"N": "43.615"}, "longitude": {"N": "-116.2023"},
    }


def test_the_added_pop_is_then_listed_last(
    answer: Handler, pops_listed: Callable[[], Any], store: SimpleNamespace,
    carriers: List[Dict[str, Any]],
) -> None:
    store.items.extend(carriers)
    answer(post_pop(BOISE))
    assert pops_listed()[-1] == {"id": 4, **BOISE}


@pytest.fixture(name="pop_request")
def pop_request_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(post_pop(BOISE))
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
    assert answer(post_pop(BOISE, "3"))["statusCode"] == 404


def test_adding_a_pop_to_an_unknown_carrier_names_the_error(served: Served) -> None:
    assert served(post_pop(BOISE, "3"))["error"] == "No such carrier"


def test_adding_a_pop_to_an_unknown_carrier_writes_nothing(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(post_pop(BOISE, "3"))
    assert store.items == []


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_adding_a_pop_to_an_id_that_is_not_a_number_answers_404(
    answer: Handler, carrier: str
) -> None:
    assert answer(post_pop(BOISE, carrier))["statusCode"] == 404


@pytest.mark.parametrize("body", MISPLACED)
def test_a_pop_that_is_not_exactly_a_located_municipality_answers_400(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], body: Any
) -> None:
    store.items.extend(carriers)
    assert answer(post_pop(body))["statusCode"] == 400


def test_a_pop_that_is_not_json_answers_400(answer: Handler) -> None:
    event = {**post_pop({}), "body": "{"}
    assert answer(event)["statusCode"] == 400


def test_a_refused_pop_names_what_is_expected(served: Served) -> None:
    assert served(post_pop({}))["error"] == POP_BODY


def test_a_refused_pop_changes_nothing(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(post_pop({}))
    assert (store.updates, len(store.items)) == ([], len(carriers))


def test_a_store_that_refuses_the_pop_answers_500(answer: Handler, store: SimpleNamespace) -> None:
    store.failing = True
    assert answer(post_pop(BOISE))["statusCode"] == 500


def test_a_store_that_refuses_the_pop_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(post_pop(BOISE))["error"] == "Failed to add the pop"


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**post_pop(BOISE), "httpMethod": "GET"})["statusCode"] == 404


def test_another_resource_answers_404(answer: Handler) -> None:
    assert answer({**post_pop(BOISE), "resource": "/carriers"})["statusCode"] == 404
