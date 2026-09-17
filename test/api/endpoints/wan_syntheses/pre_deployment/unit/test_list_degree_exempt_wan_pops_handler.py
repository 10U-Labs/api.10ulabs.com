from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from lambda_http import Handler
from synthesis_events import Served, MISSING, under

HANDLER = "lambda/list_degree_exempt_wan_pops"
DEGREE_EXEMPT_WAN_POPS = "/wan-syntheses/{id}/degree-exempt-wan-pops"


def _get_degree_exempt_wan_pops(synthesis: str = "1") -> Dict[str, Any]:
    return under(DEGREE_EXEMPT_WAN_POPS, synthesis)


def test_the_degree_exempt_wan_pops_of_a_synthesis_answer_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_degree_exempt_wan_pops())["statusCode"] == 200


def test_the_degree_exempt_wan_pops_answer_as_named_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_degree_exempt_wan_pops()) == [
        {"id": 1, "name": "Great Falls, MT"}, {"id": 2, "name": "Minot, ND"}
    ]


def test_a_synthesis_without_a_wan_still_answers_the_degree_exempt_wan_pops_it_was_given(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    exempt = served(_get_degree_exempt_wan_pops("2"))
    assert [pop["name"] for pop in exempt] == ["Columbus, OH"]


def test_the_degree_exempt_wan_pops_are_read_from_under_the_synthesis_after_its_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_degree_exempt_wan_pops())
    assert (len(store.gets), store.queries[-1]["ExpressionAttributeValues"]) == (1, {
        ":pk": {"S": "wan-syntheses/1"}, ":prefix": {"S": "degree-exempt-wan-pops/"},
    })


def test_the_degree_exempt_wan_pops_of_an_unknown_synthesis_name_the_synthesis(
    served: Served
) -> None:
    assert served(_get_degree_exempt_wan_pops("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "exempt", "-1"])
def test_the_degree_exempt_wan_pops_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_degree_exempt_wan_pops(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_the_degree_exempt_wan_pops_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(_get_degree_exempt_wan_pops())["error"]
    assert error == "Failed to read the degree-exempt wan pops"
