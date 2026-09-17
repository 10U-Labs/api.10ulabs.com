from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from lambda_http import Handler
from synthesis_events import Served, MISSING, under

HANDLER = "lambda/list_off_net"
OFF_NET = "/wan-syntheses/{id}/off-net"
DULLES = {"id": 1, "municipality": "Dulles", "state": "VA", "country": "United States",
          "latitude": 38.9519, "longitude": -77.448}
RENO = {"id": 2, "municipality": "Reno", "state": "NV", "country": "United States",
        "latitude": 39.5296, "longitude": -119.8138}


def _get_off_net(synthesis: str = "1") -> Dict[str, Any]:
    return under(OFF_NET, synthesis)


def test_the_off_net_pops_of_a_synthesis_answer_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_off_net())["statusCode"] == 200


def test_the_off_net_pops_answer_as_placed_and_unnamed_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_off_net()) == [DULLES, RENO]


def test_a_synthesis_without_a_wan_still_answers_the_off_net_pops_it_was_given(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert [pop["municipality"] for pop in served(_get_off_net("2"))] == ["Toledo"]


def test_the_off_net_pops_are_read_from_under_the_synthesis_after_its_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_off_net())
    assert (len(store.gets), store.queries[-1]["ExpressionAttributeValues"]) == (1, {
        ":pk": {"S": "wan-syntheses/1"}, ":prefix": {"S": "off-net/"},
    })


def test_the_off_net_pops_of_an_unknown_synthesis_name_the_synthesis(served: Served) -> None:
    assert served(_get_off_net("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "off-net", "-1"])
def test_the_off_net_pops_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_off_net(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_the_off_net_pops_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_off_net())["error"] == "Failed to read the off-net pops"
