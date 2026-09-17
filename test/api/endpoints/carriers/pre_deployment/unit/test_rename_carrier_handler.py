import json
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
CARRIER = "/carriers/{id}"


@pytest.fixture
def handler(endpoint: Callable[..., ModuleType]) -> ModuleType:
    return endpoint("carriers", "lambda/rename_carrier")


def _put(body: Any, carrier: str = "2") -> Dict[str, Any]:
    return {
        "resource": CARRIER, "httpMethod": "PUT", "body": json.dumps(body),
        "pathParameters": {"id": carrier},
    }


def test_a_stored_carrier_is_renamed_with_200(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert answer(_put({"name": "zayo group"}))["statusCode"] == 200


def test_a_renamed_carrier_answers_by_id_and_new_name(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert served(_put({"name": "zayo group"})) == {"id": 2, "name": "zayo group"}


def test_a_renamed_carrier_is_then_listed_by_its_new_name(
    answer: Handler, listed: Callable[[], Any], store: SimpleNamespace,
    carriers: List[Dict[str, Any]],
) -> None:
    store.items.extend(carriers)
    answer(_put({"name": "zayo group"}))
    assert listed() == [{"id": 1, "name": "lumen"}, {"id": 2, "name": "zayo group"}]


def test_a_rename_keeps_the_carrier_s_own_counters(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], lumen: Dict[str, Any]
) -> None:
    store.items.extend(carriers)
    answer(_put({"name": "lumen technologies"}, "1"))
    assert lumen["next_pop"] == {"N": "4"}


@pytest.fixture(name="rename_request")
def rename_request_fixture(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(carriers)
    answer(_put({"name": "zayo group"}))
    return dict(store.updates[0])


def test_a_rename_goes_to_the_table_the_environment_names(rename_request: Dict[str, Any]) -> None:
    assert rename_request["TableName"] == "store"


def test_a_rename_is_of_the_carrier_s_key(rename_request: Dict[str, Any]) -> None:
    assert rename_request["Key"] == {"PK": {"S": "carriers"}, "SK": {"S": "2"}}


def test_a_rename_requires_the_carrier_to_exist_in_the_store(
    rename_request: Dict[str, Any]
) -> None:
    assert rename_request["ConditionExpression"] == "attribute_exists(PK)"


def test_renaming_an_unknown_carrier_answers_404(answer: Handler) -> None:
    assert answer(_put({"name": "zayo group"}))["statusCode"] == 404


def test_renaming_an_unknown_carrier_names_the_error(served: Served) -> None:
    assert served(_put({"name": "zayo group"}))["error"] == "No such carrier"


@pytest.mark.parametrize("carrier", ["#", "", "lumen", "-1"])
def test_renaming_an_id_that_is_not_a_number_answers_404(answer: Handler, carrier: str) -> None:
    assert answer(_put({"name": "zayo group"}, carrier))["statusCode"] == 404


def test_renaming_an_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_put({"name": "zayo group"}, "#"))
    assert store.updates == []


@pytest.mark.parametrize("body", [
    {},
    {"name": 1},
    {"name": ""},
    {"name": "zayo group", "id": 9},
    ["zayo group"],
])
def test_a_rename_that_is_not_exactly_a_name_answers_400(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], body: Any
) -> None:
    store.items.extend(carriers)
    assert answer(_put(body))["statusCode"] == 400


def test_a_rename_that_is_not_json_answers_400(answer: Handler) -> None:
    event = {**_put({}), "body": "{"}
    assert answer(event)["statusCode"] == 400


def test_a_refused_rename_names_what_is_expected(served: Served) -> None:
    assert served(_put({}))["error"] == "The body must be exactly {\"name\"}"


def test_a_refused_rename_changes_nothing(
    answer: Handler, store: SimpleNamespace, carriers: List[Dict[str, Any]], zayo: Dict[str, Any]
) -> None:
    store.items.extend(carriers)
    answer(_put({}))
    assert (store.updates, zayo["name"]) == ([], {"S": "zayo"})


def test_a_store_that_refuses_the_rename_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_put({"name": "zayo group"}))["statusCode"] == 500


def test_a_store_that_refuses_the_rename_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(_put({"name": "zayo group"}))["error"]
    assert error == "Failed to update the carrier"


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**_put({"name": "zayo group"}), "httpMethod": "GET"})["statusCode"] == 404
