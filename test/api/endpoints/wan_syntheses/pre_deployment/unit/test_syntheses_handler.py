from types import SimpleNamespace
from typing import Any, Callable, Dict, List

from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
SYNTHESES = "/wan-syntheses"


def _get(resource: str = SYNTHESES) -> Dict[str, Any]:
    return {"resource": resource, "httpMethod": "GET"}


def test_an_empty_store_answers_no_syntheses(served: Served) -> None:
    assert served(_get()) == []


def test_an_empty_store_answers_200(answer: Handler) -> None:
    assert answer(_get())["statusCode"] == 200


def test_the_syntheses_answer_by_id_and_label_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get()) == [{"id": 1, "label": "minuteman"}, {"id": 2, "label": "daf"}]


def test_the_syntheses_are_read_from_the_table_the_environment_names(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_get())
    assert store.queries[0]["TableName"] == "store"


def test_the_syntheses_are_read_from_their_own_partition(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_get())
    assert store.queries[0]["ExpressionAttributeValues"] == {":pk": {"S": "wan-syntheses"}}


def test_a_store_that_refuses_the_syntheses_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_get())["statusCode"] == 500


def test_a_store_that_refuses_the_syntheses_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get())["error"] == "Failed to read the wan syntheses"


def test_another_route_answers_404(answer: Handler) -> None:
    assert answer(_get("/wan-synthesizer/tenants"))["statusCode"] == 404
