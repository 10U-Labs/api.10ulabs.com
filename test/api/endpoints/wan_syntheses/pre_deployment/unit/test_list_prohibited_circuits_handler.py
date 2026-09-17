from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from lambda_http import Handler
from synthesis_events import Served, MISSING, under

HANDLER = "lambda/list_prohibited_circuits"
PROHIBITED_CIRCUITS = "/wan-syntheses/{id}/prohibited-circuits"


def _get_prohibited_circuits(synthesis: str = "1") -> Dict[str, Any]:
    return under(PROHIBITED_CIRCUITS, synthesis)


def test_the_prohibited_circuits_of_a_synthesis_answer_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_prohibited_circuits())["statusCode"] == 200


def test_the_prohibited_circuits_answer_between_named_pops_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_prohibited_circuits()) == [
        {"id": 1, "source": "Ashburn, VA", "target": "Minot, ND"},
        {"id": 2, "source": "Minot, ND", "target": "Great Falls, MT"},
    ]


def test_a_synthesis_without_a_wan_still_answers_the_prohibited_circuits_it_was_given(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert [one["target"] for one in served(_get_prohibited_circuits("2"))] == ["Cleveland, OH"]


def test_the_prohibited_circuits_are_read_from_under_the_synthesis_after_its_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_prohibited_circuits())
    assert (len(store.gets), store.queries[-1]["ExpressionAttributeValues"]) == (1, {
        ":pk": {"S": "wan-syntheses/1"}, ":prefix": {"S": "prohibited-circuits/"},
    })


def test_the_prohibited_circuits_of_an_unknown_synthesis_name_the_synthesis(
    served: Served
) -> None:
    assert served(_get_prohibited_circuits("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "banned", "-1"])
def test_the_prohibited_circuits_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_prohibited_circuits(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_the_prohibited_circuits_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(_get_prohibited_circuits())["error"]
    assert error == "Failed to read the prohibited circuits"
