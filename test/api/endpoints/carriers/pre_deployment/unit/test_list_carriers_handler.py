from types import SimpleNamespace
from typing import Any, Callable, Dict, List

from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/list_carriers"
CARRIERS = "/carriers"


def _get(resource: str = CARRIERS) -> Dict[str, Any]:
    return {"resource": resource, "httpMethod": "GET"}


def test_an_empty_store_answers_no_carriers(served: Served) -> None:
    assert served(_get()) == []


def test_an_empty_store_answers_200(answer: Handler) -> None:
    assert answer(_get())["statusCode"] == 200


def test_the_carriers_answer_by_id_and_name_in_id_order(
    served: Served, store: SimpleNamespace, carriers: List[Dict[str, Any]]
) -> None:
    store.items.extend(carriers)
    listed = served(_get())
    assert listed == [{"id": 1, "name": "lumen"}, {"id": 2, "name": "zayo"}]


def test_the_carriers_are_read_from_the_table_the_environment_names(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_get())
    assert store.queries[0]["TableName"] == "store"


def test_the_carriers_are_read_from_their_own_partition(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_get())
    assert store.queries[0]["ExpressionAttributeValues"] == {":pk": {"S": "carriers"}}


def test_a_store_that_refuses_the_read_answers_500(answer: Handler, store: SimpleNamespace) -> None:
    store.failing = True
    assert answer(_get())["statusCode"] == 500


def test_a_store_that_refuses_the_read_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get())["error"] == "Failed to read the carriers"


def test_another_resource_answers_404(answer: Handler) -> None:
    assert answer(_get("/pops"))["statusCode"] == 404


def test_another_verb_answers_404(answer: Handler) -> None:
    assert answer({**_get(), "httpMethod": "POST"})["statusCode"] == 404
