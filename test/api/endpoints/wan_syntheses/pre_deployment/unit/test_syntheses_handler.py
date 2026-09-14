from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

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


SYNTHESIS = "/wan-syntheses/{synthesis}"
MISSING = "No such wan synthesis"
MINUTEMAN = {
    "id": 1, "label": "minuteman",
    "wan_pop_count": {"min": 3, "max": 6}, "backbone_number_of_diverse_circuits": 3,
    "homing_degree": 2, "convergence_promotion": False,
    "knobs": {"coverage_target_miles": 1200},
    "settings": {"compass_sector_count": 8, "wan_pop_search_memory_share": 0.6},
    "status": "success",
    "coverage": {"delivered_miles": 1250.5, "target_miles": 1200},
    "fiber_miles": 4321.125, "backbone_lower_bound_miles": 3900,
    "homing_miles": {"tenant": 210.25, "provider": 80},
    "diverse_circuits": {"number_of_diverse_circuits": 3, "ceilings": [3, 2]},
}


def _get_one(synthesis: str) -> Dict[str, Any]:
    return {**_get(SYNTHESIS), "pathParameters": {"synthesis": synthesis}}


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


WAN_POPS = "/wan-syntheses/{synthesis}/wan-pops"
NO_WAN = "The synthesis has no wan"
ASHBURN = {"id": 1, "name": "Ashburn, VA", "municipality": "Ashburn", "state": "VA",
           "country": "US", "latitude": 39.0438, "longitude": -77.4874, "carrier": "zayo"}
CHEYENNE = {"id": 2, "name": "Cheyenne, WY", "municipality": "Cheyenne", "state": "WY",
            "country": "US", "latitude": 41.14, "longitude": -104.8202, "carrier": "lumen"}


def _get_wan_pops(synthesis: str = "1") -> Dict[str, Any]:
    return {**_get(WAN_POPS), "pathParameters": {"synthesis": synthesis}}


def test_the_wan_pops_of_a_synthesis_answer_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_wan_pops())["statusCode"] == 200


def test_the_wan_pops_answer_as_placed_carrier_pops_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_wan_pops()) == [ASHBURN, CHEYENNE]


@pytest.fixture(name="wan_pops_read")
def wan_pops_read_fixture(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> SimpleNamespace:
    store.items.extend(syntheses)
    answer(_get_wan_pops())
    return store


def test_the_wan_pops_are_read_after_the_synthesis_s_record(wan_pops_read: SimpleNamespace) -> None:
    assert [one["Key"] for one in wan_pops_read.gets] == [
        {"PK": {"S": "wan-syntheses"}, "SK": {"S": "1"}},
    ]


def test_the_wan_pops_are_read_from_under_the_synthesis(wan_pops_read: SimpleNamespace) -> None:
    assert wan_pops_read.queries[-1]["ExpressionAttributeValues"] == {
        ":pk": {"S": "wan-syntheses/1"}, ":prefix": {"S": "wan-pops/"},
    }


def test_the_wan_pops_are_read_from_the_table_the_environment_names(
    wan_pops_read: SimpleNamespace
) -> None:
    assert wan_pops_read.queries[-1]["TableName"] == "store"


def test_a_synthesis_without_a_wan_has_no_wan_pops(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_wan_pops("2"))["statusCode"] == 404


def test_a_synthesis_without_a_wan_names_the_error(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_wan_pops("2"))["error"] == NO_WAN


def test_a_synthesis_without_a_wan_is_not_queried(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_wan_pops("2"))
    assert store.queries == []


def test_the_wan_pops_of_an_unknown_synthesis_answer_404(answer: Handler) -> None:
    assert answer(_get_wan_pops("3"))["statusCode"] == 404


def test_the_wan_pops_of_an_unknown_synthesis_name_the_synthesis(served: Served) -> None:
    assert served(_get_wan_pops("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "minuteman", "-1"])
def test_the_wan_pops_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_wan_pops(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_the_wan_pops_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_get_wan_pops())["statusCode"] == 500


def test_a_store_that_refuses_the_wan_pops_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_wan_pops())["error"] == "Failed to read the wan pops"
