import json
from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/create_carrier"
CARRIERS = "/carriers"


def _post(body: Any, resource: str = CARRIERS) -> Dict[str, Any]:
    return {"resource": resource, "httpMethod": "POST", "body": json.dumps(body)}


def _counter(store: SimpleNamespace) -> Dict[str, Any]:
    return next(item for item in store.items if item["SK"] == {"S": "#"})


def test_a_carrier_is_created_with_201(answer: Handler) -> None:
    assert answer(_post({"name": "lumen"}))["statusCode"] == 201


def test_the_first_carrier_is_number_one(served: Served) -> None:
    assert served(_post({"name": "lumen"})) == {"id": 1, "name": "lumen"}


def test_the_created_carrier_is_located_under_the_collection(answer: Handler) -> None:
    headers = answer(_post({"name": "lumen"}))["headers"]
    assert headers["Location"] == "/carriers/1"


def test_the_id_is_the_next_the_counter_holds(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_post({"name": "cogent"}))["id"] == 3


def test_the_counter_moves_past_the_id_it_gave(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_post({"name": "cogent"}))
    assert _counter(store)["next"] == {"N": "4"}


def test_an_id_is_never_reused(served: Served) -> None:
    given = [served(_post({"name": name}))["id"] for name in ("lumen", "zayo")]
    assert given == [1, 2]


def test_the_counter_is_advanced_in_the_table_the_environment_names(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_post({"name": "lumen"}))
    assert store.updates[0]["TableName"] == "store"


def test_the_counter_is_the_hash_item_of_the_collection(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_post({"name": "lumen"}))
    assert store.updates[0]["Key"] == {"PK": {"S": "carriers"}, "SK": {"S": "#"}}


def test_the_carrier_is_written_with_its_own_counters_at_one(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    answer(_post({"name": "cogent"}))
    assert store.items[-1] == {
        "PK": {"S": "carriers"}, "SK": {"S": "3"}, "name": {"S": "cogent"},
        "next_pop": {"N": "1"}, "next_fiber_segment": {"N": "1"},
    }


def test_the_created_carrier_is_then_listed(answer: Handler, listed: Callable[[], Any]) -> None:
    answer(_post({"name": "lumen"}))
    assert listed() == [{"id": 1, "name": "lumen"}]


@pytest.mark.parametrize("body", [
    {},
    {"name": 1},
    {"name": ""},
    {"name": "lumen", "id": 9},
    ["lumen"],
])
def test_a_body_that_is_not_exactly_a_name_answers_400(answer: Handler, body: Any) -> None:
    assert answer(_post(body))["statusCode"] == 400


def test_a_body_that_is_not_json_answers_400(answer: Handler) -> None:
    event = {"resource": CARRIERS, "httpMethod": "POST", "body": "{"}
    assert answer(event)["statusCode"] == 400


def test_a_refused_body_names_what_is_expected(served: Served) -> None:
    assert served(_post({}))["error"] == "The body must be exactly {\"name\"}"


def test_a_refused_body_writes_nothing(answer: Handler, store: SimpleNamespace) -> None:
    answer(_post({}))
    assert store.items == []


def test_a_store_that_refuses_the_write_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_post({"name": "lumen"}))["statusCode"] == 500


def test_a_store_that_refuses_the_write_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(_post({"name": "lumen"}))["error"]
    assert error == "Failed to create the carrier"


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**_post({"name": "lumen"}), "httpMethod": "GET"})["statusCode"] == 404


def test_another_resource_answers_404(answer: Handler) -> None:
    assert answer(_post({"name": "lumen"}, "/carriers/{id}"))["statusCode"] == 404
