from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
HANDLER = "lambda/delete_wan_synthesis"
SYNTHESIS = "/wan-syntheses/{id}"
MISSING = "No such wan synthesis"


def _delete(synthesis: str) -> Dict[str, Any]:
    return {
        "resource": SYNTHESIS, "httpMethod": "DELETE", "pathParameters": {"id": synthesis},
    }


@pytest.fixture(name="deleted")
def deleted_fixture(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(syntheses)
    return answer(_delete("1"))


def test_a_finished_synthesis_is_deleted_with_204(deleted: Dict[str, Any]) -> None:
    assert deleted["statusCode"] == 204


@pytest.mark.usefixtures("deleted")
def test_a_deleted_synthesis_is_gone_with_everything_under_it(store: SimpleNamespace) -> None:
    assert [
        item["SK"]["S"] for item in store.items
        if item["PK"]["S"] in ("wan-syntheses/1",) or item["SK"]["S"] == "1"
    ] == []


@pytest.mark.usefixtures("deleted")
def test_a_deletion_leaves_the_other_syntheses_alone(store: SimpleNamespace) -> None:
    kept = sorted(item["SK"]["S"] for item in store.items if item["PK"]["S"] == "wan-syntheses")
    assert kept == ["#", "2"]


@pytest.mark.usefixtures("deleted")
def test_a_deletion_leaves_what_is_under_the_other_syntheses(store: SimpleNamespace) -> None:
    assert {item["PK"]["S"] for item in store.items} == {"wan-syntheses", "wan-syntheses/2"}


@pytest.mark.usefixtures("deleted")
def test_the_record_is_deleted_last_and_must_exist(store: SimpleNamespace) -> None:
    assert (store.deletes[-1]["Key"], store.deletes[-1]["ConditionExpression"]) == (
        {"PK": {"S": "wan-syntheses"}, "SK": {"S": "1"}}, "attribute_exists(PK)",
    )


@pytest.mark.parametrize("status", ["creating", "synthesizing"])
def test_a_synthesis_still_running_answers_409(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]], status: str
) -> None:
    store.items.extend(syntheses)
    store.items[1]["status"] = {"S": status}
    assert answer(_delete("2"))["statusCode"] == 409


def test_a_synthesis_still_running_names_the_refusal(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    store.items[1]["status"] = {"S": "synthesizing"}
    assert served(_delete("2"))["error"] == "The synthesis is still running"


def test_a_synthesis_still_running_is_left_whole(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    store.items[1]["status"] = {"S": "creating"}
    answer(_delete("2"))
    assert store.deletes == []


def test_deleting_an_unknown_synthesis_answers_404(answer: Handler) -> None:
    assert answer(_delete("3"))["statusCode"] == 404


def test_deleting_an_unknown_synthesis_names_the_error(served: Served) -> None:
    assert served(_delete("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "minuteman", "-1"])
def test_deleting_an_id_that_is_not_a_number_answers_404_and_reads_nothing(
    answer: Handler, store: SimpleNamespace, synthesis: str
) -> None:
    assert (answer(_delete(synthesis))["statusCode"], store.gets) == (404, [])


def test_a_store_that_refuses_the_deletion_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_delete("1"))["statusCode"] == 500


def test_a_store_that_refuses_the_deletion_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_delete("1"))["error"] == "Failed to delete the wan synthesis"


def test_a_put_on_a_synthesis_answers_404(answer: Handler) -> None:
    event = {"resource": SYNTHESIS, "httpMethod": "PUT", "pathParameters": {"id": "1"}}
    assert answer(event)["statusCode"] == 404
