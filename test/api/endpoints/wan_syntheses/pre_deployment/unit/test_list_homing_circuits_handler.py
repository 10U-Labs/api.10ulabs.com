from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from lambda_http import Handler
from synthesis_events import Served, MISSING, NO_WAN, get

HANDLER = "lambda/list_homing_circuits"
HOMING_CIRCUITS = "/wan-syntheses/{id}/homing-circuits"
MINOT_HOME = {"id": 1, "source_id": 1, "homing_kind": "tenant_to_backbone", "target": 2,
              "route": ["Minot, ND", "Cheyenne, WY"], "distance_miles": 590}
COLUMBUS_HOME = {"id": 2, "source_id": 1, "homing_kind": "provider_to_backbone", "target": 1,
                 "route": ["Columbus, OH", "Ashburn, VA"], "distance_miles": 331.25}


def _get_homing_circuits(synthesis: str = "1") -> Dict[str, Any]:
    return {**get(HOMING_CIRCUITS), "pathParameters": {"id": synthesis}}


def test_the_homing_circuits_of_a_synthesis_answer_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_homing_circuits())["statusCode"] == 200


def test_the_homing_circuits_answer_from_a_kinded_source_to_a_wan_pop_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_homing_circuits()) == [MINOT_HOME, COLUMBUS_HOME]


def test_the_homing_circuits_are_read_from_under_the_synthesis_after_its_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_homing_circuits())
    assert (len(store.gets), store.queries[-1]["ExpressionAttributeValues"]) == (1, {
        ":pk": {"S": "wan-syntheses/1"}, ":prefix": {"S": "homing-circuits/"},
    })


def test_a_synthesis_without_a_wan_has_no_homing_circuits(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_homing_circuits("2"))["error"] == NO_WAN


def test_the_homing_circuits_of_an_unknown_synthesis_name_the_synthesis(served: Served) -> None:
    assert served(_get_homing_circuits("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "minuteman", "-1"])
def test_the_homing_circuits_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_homing_circuits(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_the_homing_circuits_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_homing_circuits())["error"] == "Failed to read the homing circuits"
