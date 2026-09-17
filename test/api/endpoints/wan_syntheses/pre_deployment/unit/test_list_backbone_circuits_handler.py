from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from lambda_http import Handler
from synthesis_events import Served, MISSING, NO_WAN, get

HANDLER = "lambda/list_backbone_circuits"
BACKBONE_CIRCUITS = "/wan-syntheses/{id}/backbone-circuits"
NORTHERN = {"id": 1, "source": 1, "target": 2, "distance_miles": 1480,
            "route": ["Ashburn, VA", "Chicago, IL", "Cheyenne, WY"],
            "reason": "circuit_for_target", "requested_by": []}
SOUTHERN = {"id": 2, "source": 2, "target": 1, "distance_miles": 1612.5,
            "route": ["Cheyenne, WY", "Omaha, NE", "Ashburn, VA"],
            "reason": "circuit_for_target", "requested_by": ["Minot, ND"]}


def _get_backbone_circuits(synthesis: str = "1") -> Dict[str, Any]:
    return {**get(BACKBONE_CIRCUITS), "pathParameters": {"id": synthesis}}


def test_the_backbone_circuits_of_a_synthesis_answer_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_backbone_circuits())["statusCode"] == 200


def test_the_backbone_circuits_answer_between_wan_pops_by_id_with_their_route_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_backbone_circuits()) == [NORTHERN, SOUTHERN]


def test_the_backbone_circuits_are_read_from_under_the_synthesis_after_its_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_backbone_circuits())
    assert (len(store.gets), store.queries[-1]["ExpressionAttributeValues"]) == (1, {
        ":pk": {"S": "wan-syntheses/1"}, ":prefix": {"S": "backbone-circuits/"},
    })


def test_a_synthesis_without_a_wan_has_no_backbone_circuits(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_backbone_circuits("2"))["error"] == NO_WAN


def test_the_backbone_circuits_of_an_unknown_synthesis_name_the_synthesis(served: Served) -> None:
    assert served(_get_backbone_circuits("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "minuteman", "-1"])
def test_the_backbone_circuits_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_backbone_circuits(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_the_backbone_circuits_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_backbone_circuits())["error"] == "Failed to read the backbone circuits"
