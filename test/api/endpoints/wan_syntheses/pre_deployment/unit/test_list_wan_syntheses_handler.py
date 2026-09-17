from types import SimpleNamespace
from typing import Any, Dict, List

from lambda_http import Handler
from synthesis_events import Served, get

HANDLER = "lambda/list_wan_syntheses"


def test_an_empty_store_answers_no_syntheses(served: Served) -> None:
    assert served(get()) == []


def test_an_empty_store_answers_200(answer: Handler) -> None:
    assert answer(get())["statusCode"] == 200


def test_the_syntheses_answer_by_id_and_label_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(get()) == [{"id": 1, "label": "minuteman"}, {"id": 2, "label": "daf"}]


def test_the_syntheses_are_read_from_the_table_the_environment_names(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(get())
    assert store.queries[0]["TableName"] == "store"


def test_the_syntheses_are_read_from_their_own_partition(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(get())
    assert store.queries[0]["ExpressionAttributeValues"] == {":pk": {"S": "wan-syntheses"}}


def test_a_store_that_refuses_the_syntheses_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(get())["statusCode"] == 500


def test_a_store_that_refuses_the_syntheses_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(get())["error"] == "Failed to read the wan syntheses"


def test_another_route_answers_404(answer: Handler) -> None:
    assert answer(get("/wan-synthesizer/tenants"))["statusCode"] == 404
