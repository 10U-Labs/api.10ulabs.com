from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from lambda_http import Handler
from synthesis_events import Served, MISSING, get

HANDLER = "lambda/read_wan_synthesis"
SYNTHESIS = "/wan-syntheses/{id}"
MINUTEMAN = {
    "id": 1, "label": "minuteman",
    "wan_pop_count": {"min": 3, "max": 6}, "backbone_number_of_diverse_circuits": 3,
    "homing_degree": 2, "convergence_promotion": False,
    "knobs": {"backbone_coverage_target_miles": 1200},
    "settings": {"compass_sector_count": 8, "wan_pop_search_memory_share": 0.6},
    "status": "success",
    "coverage": {"delivered_miles": 1250.5, "target_miles": 1200},
    "fiber_miles": 4321.125, "backbone_lower_bound_miles": 3900,
    "homing_miles": {"tenant": 210.25, "provider": 80},
    "diverse_circuits": {"number_of_diverse_circuits": 3, "ceilings": [3, 2]},
}


def _get_one(synthesis: str) -> Dict[str, Any]:
    return {**get(SYNTHESIS), "pathParameters": {"id": synthesis}}


def test_a_stored_synthesis_answers_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_one("1"))["statusCode"] == 200


def test_a_stored_synthesis_answers_its_whole_record_with_its_id(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_one("1")) == MINUTEMAN


def test_a_failed_synthesis_answers_200_with_its_reason(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    failed = served(_get_one("2"))
    assert (failed["status"], failed["reason"]) == ("fail", "No 2-vertex-connected backbone")


def test_a_synthesis_is_read_from_the_table_the_environment_names(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_get_one("1"))
    assert store.gets[0]["TableName"] == "store"


def test_a_synthesis_is_read_by_its_key_in_the_collection(
    answer: Handler, store: SimpleNamespace
) -> None:
    answer(_get_one("1"))
    assert store.gets[0]["Key"] == {"PK": {"S": "wan-syntheses"}, "SK": {"S": "1"}}


def test_an_unknown_synthesis_answers_404(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_one("3"))["statusCode"] == 404


def test_an_unknown_synthesis_names_the_error(served: Served) -> None:
    assert served(_get_one("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "minuteman", "-1"])
def test_a_synthesis_id_that_is_not_a_number_answers_404(answer: Handler, synthesis: str) -> None:
    assert answer(_get_one(synthesis))["statusCode"] == 404


@pytest.mark.parametrize("synthesis", ["#", "", "minuteman", "-1"])
def test_a_synthesis_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, synthesis: str
) -> None:
    answer(_get_one(synthesis))
    assert store.gets == []


def test_a_store_that_refuses_the_synthesis_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_get_one("1"))["statusCode"] == 500


def test_a_store_that_refuses_the_synthesis_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_one("1"))["error"] == "Failed to read the wan synthesis"
