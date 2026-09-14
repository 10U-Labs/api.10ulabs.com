import json
from types import ModuleType, SimpleNamespace
from typing import Any, Dict, List

CARRIERS = "/carriers"


def _get(resource: str = CARRIERS) -> Dict[str, Any]:
    return {"resource": resource, "httpMethod": "GET"}


def _answer(carriers_handler: ModuleType, event: Dict[str, Any]) -> Dict[str, Any]:
    return dict(carriers_handler.lambda_handler(event, None))


def _body(carriers_handler: ModuleType, event: Dict[str, Any]) -> Any:
    return json.loads(_answer(carriers_handler, event)["body"])


def test_an_empty_store_answers_no_carriers(carriers_handler: ModuleType) -> None:
    assert _body(carriers_handler, _get()) == []


def test_an_empty_store_answers_200(carriers_handler: ModuleType) -> None:
    assert _answer(carriers_handler, _get())["statusCode"] == 200


def test_the_carriers_answer_by_id_and_name_in_id_order(
    carriers_handler: ModuleType, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    assert _body(carriers_handler, _get()) == [{"id": 1, "name": "lumen"}, {"id": 2, "name": "zayo"}]


def test_the_carriers_are_read_from_the_table_the_environment_names(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    _answer(carriers_handler, _get())
    assert store.queries[0]["TableName"] == "store"


def test_the_carriers_are_read_from_their_own_partition(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    _answer(carriers_handler, _get())
    assert store.queries[0]["ExpressionAttributeValues"] == {":pk": {"S": "carriers"}}


def test_a_store_that_refuses_the_read_answers_500(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert _answer(carriers_handler, _get())["statusCode"] == 500


def test_a_store_that_refuses_the_read_names_the_error(
    carriers_handler: ModuleType, store: SimpleNamespace
) -> None:
    store.failing = True
    assert _body(carriers_handler, _get())["error"] == "Failed to read the carriers"


def test_another_resource_answers_404(carriers_handler: ModuleType) -> None:
    assert _answer(carriers_handler, _get("/carriers/{carrier}"))["statusCode"] == 404
