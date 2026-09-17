from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from lambda_http import Handler
from synthesis_events import Served, MISSING, NO_WAN, get

HANDLER = "lambda/list_ridden_fiber"
RIDDEN_FIBER = "/wan-syntheses/{id}/fiber-segments"
IAD_ORD = {"id": 1, "carrier": "zayo", "a_municipality": "Ashburn", "a_state": "VA",
           "a_latitude": 39.0438, "a_longitude": -77.4874, "z_municipality": "Chicago",
           "z_state": "IL", "z_latitude": 41.8781, "z_longitude": -87.6298,
           "distance_miles": 599.5, "submarine": False}
ORD_CYS = {"id": 2, "carrier": "lumen", "a_municipality": "Chicago", "a_state": "IL",
           "a_latitude": 41.8781, "a_longitude": -87.6298, "z_municipality": "Cheyenne",
           "z_state": "WY", "z_latitude": 41.14, "z_longitude": -104.8202,
           "distance_miles": 880.5, "submarine": False}


def _get_ridden_fiber(synthesis: str = "1") -> Dict[str, Any]:
    return {**get(RIDDEN_FIBER), "pathParameters": {"id": synthesis}}


def test_the_fiber_a_synthesis_rides_answers_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_ridden_fiber())["statusCode"] == 200


def test_the_fiber_a_synthesis_rides_answers_as_placed_carrier_segments_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_ridden_fiber()) == [IAD_ORD, ORD_CYS]


def test_the_ridden_fiber_is_read_from_under_the_synthesis_after_its_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_ridden_fiber())
    assert (len(store.gets), store.queries[-1]["ExpressionAttributeValues"]) == (1, {
        ":pk": {"S": "wan-syntheses/1"}, ":prefix": {"S": "fiber-segments/"},
    })


def test_a_synthesis_without_a_wan_rides_no_fiber(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_ridden_fiber("2"))["error"] == NO_WAN


def test_the_ridden_fiber_of_an_unknown_synthesis_names_the_synthesis(served: Served) -> None:
    assert served(_get_ridden_fiber("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "minuteman", "-1"])
def test_the_ridden_fiber_of_an_id_that_is_not_a_number_answers_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_ridden_fiber(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_the_ridden_fiber_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_ridden_fiber())["error"] == "Failed to read the fiber segments"
