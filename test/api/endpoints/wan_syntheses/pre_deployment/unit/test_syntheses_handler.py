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


WAN_POP = "/wan-syntheses/{synthesis}/wan-pops/{wan-pop}"
MISSING_WAN_POP = "No such wan pop"


def _get_wan_pop(synthesis: str = "1", wan_pop: str = "2") -> Dict[str, Any]:
    return {**_get(WAN_POP), "pathParameters": {"synthesis": synthesis, "wan-pop": wan_pop}}


def test_a_stored_wan_pop_answers_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_wan_pop())["statusCode"] == 200


def test_a_stored_wan_pop_answers_as_a_placed_carrier_pop_with_its_id(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_wan_pop()) == CHEYENNE


@pytest.fixture(name="wan_pop_gets")
def wan_pop_gets_fixture(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    store.items.extend(syntheses)
    answer(_get_wan_pop())
    return [dict(one) for one in store.gets]


def test_a_wan_pop_is_read_after_the_synthesis_s_record(wan_pop_gets: List[Dict[str, Any]]) -> None:
    assert [one["Key"] for one in wan_pop_gets] == [
        {"PK": {"S": "wan-syntheses"}, "SK": {"S": "1"}},
        {"PK": {"S": "wan-syntheses/1"}, "SK": {"S": "wan-pops/2"}},
    ]


def test_a_wan_pop_is_read_from_the_table_the_environment_names(
    wan_pop_gets: List[Dict[str, Any]]
) -> None:
    assert [one["TableName"] for one in wan_pop_gets] == ["store", "store"]


def test_a_wan_pop_of_a_synthesis_without_a_wan_answers_404(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_wan_pop("2", "1"))["statusCode"] == 404


def test_a_wan_pop_of_a_synthesis_without_a_wan_names_the_wan(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_wan_pop("2", "1"))["error"] == NO_WAN


def test_a_wan_pop_of_a_synthesis_without_a_wan_is_not_looked_for(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_wan_pop("2", "1"))
    assert len(store.gets) == 1


def test_a_wan_pop_of_an_unknown_synthesis_answers_404(answer: Handler) -> None:
    assert answer(_get_wan_pop("3"))["statusCode"] == 404


def test_a_wan_pop_of_an_unknown_synthesis_names_the_synthesis(served: Served) -> None:
    assert served(_get_wan_pop("3"))["error"] == MISSING


def test_an_unknown_wan_pop_answers_404(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_wan_pop("1", "3"))["statusCode"] == 404


def test_an_unknown_wan_pop_names_the_wan_pop(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_wan_pop("1", "3"))["error"] == MISSING_WAN_POP


@pytest.mark.parametrize("wan_pop", ["#", "", "2/", "-1"])
def test_a_wan_pop_id_that_is_not_a_number_answers_404(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]], wan_pop: str
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_wan_pop("1", wan_pop))["statusCode"] == 404


@pytest.mark.parametrize("wan_pop", ["#", "", "2/", "-1"])
def test_a_wan_pop_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, wan_pop: str
) -> None:
    answer(_get_wan_pop("1", wan_pop))
    assert store.gets == []


def test_a_store_that_refuses_the_wan_pop_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_get_wan_pop())["statusCode"] == 500


def test_a_store_that_refuses_the_wan_pop_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_wan_pop())["error"] == "Failed to read the wan pop"


BACKBONE_CIRCUITS = "/wan-syntheses/{synthesis}/backbone-circuits"
NORTHERN = {"id": 1, "source": 1, "target": 2, "distance_miles": 1480,
            "route": ["Ashburn, VA", "Chicago, IL", "Cheyenne, WY"],
            "reason": "circuit_for_target", "requested_by": []}
SOUTHERN = {"id": 2, "source": 2, "target": 1, "distance_miles": 1612.5,
            "route": ["Cheyenne, WY", "Omaha, NE", "Ashburn, VA"],
            "reason": "circuit_for_target", "requested_by": ["Minot, ND"]}


def _get_backbone_circuits(synthesis: str = "1") -> Dict[str, Any]:
    return {**_get(BACKBONE_CIRCUITS), "pathParameters": {"synthesis": synthesis}}


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


HOMING_CIRCUITS = "/wan-syntheses/{synthesis}/homing-circuits"
MINOT_HOME = {"id": 1, "source_id": 1, "homing_kind": "tenant_to_backbone", "target": 2,
              "route": ["Minot, ND", "Cheyenne, WY"], "distance_miles": 590}
COLUMBUS_HOME = {"id": 2, "source_id": 1, "homing_kind": "provider_to_backbone", "target": 1,
                 "route": ["Columbus, OH", "Ashburn, VA"], "distance_miles": 331.25}


def _get_homing_circuits(synthesis: str = "1") -> Dict[str, Any]:
    return {**_get(HOMING_CIRCUITS), "pathParameters": {"synthesis": synthesis}}


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


RIDDEN_FIBER = "/wan-syntheses/{synthesis}/fiber-segments"
IAD_ORD = {"id": 1, "carrier": "zayo", "a_municipality": "Ashburn", "a_state": "VA",
           "a_latitude": 39.0438, "a_longitude": -77.4874, "z_municipality": "Chicago",
           "z_state": "IL", "z_latitude": 41.8781, "z_longitude": -87.6298,
           "distance_miles": 599.5, "submarine": False}
ORD_CYS = {"id": 2, "carrier": "lumen", "a_municipality": "Chicago", "a_state": "IL",
           "a_latitude": 41.8781, "a_longitude": -87.6298, "z_municipality": "Cheyenne",
           "z_state": "WY", "z_latitude": 41.14, "z_longitude": -104.8202,
           "distance_miles": 880.5, "submarine": False}


def _get_ridden_fiber(synthesis: str = "1") -> Dict[str, Any]:
    return {**_get(RIDDEN_FIBER), "pathParameters": {"synthesis": synthesis}}


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


SITES = "/wan-syntheses/{synthesis}/sites"
WARREN = {"id": 1, "name": "F.E. Warren AFB", "municipality": "Cheyenne", "state": "WY",
          "country": "United States", "latitude": 41.1517, "longitude": -104.8678,
          "exempt_from_distance_constraint": False}
HILL = {"id": 2, "name": "Hill AFB", "municipality": "Layton", "state": "UT",
        "country": "United States", "latitude": 41.124, "longitude": -111.9731,
        "exempt_from_distance_constraint": False}


def _get_sites(synthesis: str = "1") -> Dict[str, Any]:
    return {**_get(SITES), "pathParameters": {"synthesis": synthesis}}


def test_the_sites_of_a_synthesis_answer_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_sites())["statusCode"] == 200


def test_the_sites_answer_as_named_and_placed_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_sites()) == [WARREN, HILL]


def test_a_synthesis_without_a_wan_still_answers_the_sites_it_was_given(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert [site["name"] for site in served(_get_sites("2"))] == ["Wright-Patterson AFB"]


def test_the_sites_are_read_from_under_the_synthesis_after_its_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_sites())
    assert (len(store.gets), store.queries[-1]["ExpressionAttributeValues"]) == (1, {
        ":pk": {"S": "wan-syntheses/1"}, ":prefix": {"S": "sites/"},
    })


def test_the_sites_of_an_unknown_synthesis_name_the_synthesis(served: Served) -> None:
    assert served(_get_sites("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "minuteman", "-1"])
def test_the_sites_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_sites(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_the_sites_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_sites())["error"] == "Failed to read the sites"


SITE = "/wan-syntheses/{synthesis}/sites/{site}"
MISSING_SITE = "No such site"


def _get_site(synthesis: str = "1", site: str = "2") -> Dict[str, Any]:
    return {**_get(SITE), "pathParameters": {"synthesis": synthesis, "site": site}}


def test_a_stored_site_answers_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_site())["statusCode"] == 200


def test_a_stored_site_answers_as_named_and_placed_with_its_id(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_site()) == HILL


def test_a_site_is_read_by_its_key_after_the_synthesis_s_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_site())
    assert [one["Key"] for one in store.gets] == [
        {"PK": {"S": "wan-syntheses"}, "SK": {"S": "1"}},
        {"PK": {"S": "wan-syntheses/1"}, "SK": {"S": "sites/2"}},
    ]


def test_a_synthesis_without_a_wan_still_serves_a_site_it_was_given(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_site("2", "1"))["name"] == "Wright-Patterson AFB"


def test_a_site_of_an_unknown_synthesis_names_the_synthesis(served: Served) -> None:
    assert served(_get_site("3"))["error"] == MISSING


def test_an_unknown_site_answers_404(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_site("1", "3"))["statusCode"] == 404


def test_an_unknown_site_names_the_site(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_site("1", "3"))["error"] == MISSING_SITE


@pytest.mark.parametrize("site", ["#", "", "2/", "-1"])
def test_a_site_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, site: str
) -> None:
    assert (answer(_get_site("1", site))["statusCode"], store.gets) == (404, [])


def test_a_store_that_refuses_the_site_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_site())["error"] == "Failed to read the site"


RUN_REGIONS = "/wan-syntheses/{synthesis}/hyperscale-cloud-service-provider-regions"
PROVIDER_A = {"id": 1, "name": "Provider A", "municipality": "Columbus", "state": "OH",
              "country": "United States", "latitude": 39.9612, "longitude": -82.9988}
PROVIDER_B = {"id": 2, "name": "Provider B", "municipality": "Boardman", "state": "OR",
              "country": "United States", "latitude": 45.8396, "longitude": -119.7006}


def _get_run_regions(synthesis: str = "1") -> Dict[str, Any]:
    return {**_get(RUN_REGIONS), "pathParameters": {"synthesis": synthesis}}


def test_the_regions_of_a_synthesis_answer_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_run_regions())["statusCode"] == 200


def test_the_regions_of_a_synthesis_answer_as_the_catalog_serves_them_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_run_regions()) == [PROVIDER_A, PROVIDER_B]


def test_a_synthesis_without_a_wan_still_answers_the_regions_it_was_given(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert [region["name"] for region in served(_get_run_regions("2"))] == ["Provider D"]


def test_the_regions_of_a_synthesis_are_read_from_under_it_after_its_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_run_regions())
    assert (len(store.gets), store.queries[-1]["ExpressionAttributeValues"]) == (1, {
        ":pk": {"S": "wan-syntheses/1"},
        ":prefix": {"S": "hyperscale-cloud-service-provider-regions/"},
    })


def test_the_regions_of_an_unknown_synthesis_name_the_synthesis(served: Served) -> None:
    assert served(_get_run_regions("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "minuteman", "-1"])
def test_the_regions_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_run_regions(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_a_synthesis_s_regions_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(_get_run_regions())["error"]
    assert error == "Failed to read the hyperscale cloud service provider regions"


RUN_REGION = "/wan-syntheses/{synthesis}/hyperscale-cloud-service-provider-regions/{region}"
MISSING_REGION = "No such hyperscale cloud service provider region"


def _get_run_region(synthesis: str = "1", region: str = "2") -> Dict[str, Any]:
    return {**_get(RUN_REGION), "pathParameters": {"synthesis": synthesis, "region": region}}


def test_a_stored_region_of_a_synthesis_answers_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_run_region())["statusCode"] == 200


def test_a_region_of_a_synthesis_answers_as_the_catalog_serves_it_with_its_id(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_run_region()) == PROVIDER_B


def test_a_region_of_a_synthesis_is_read_by_its_key_after_the_synthesis_s_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_run_region())
    assert [one["Key"]["SK"]["S"] for one in store.gets] == [
        "1", "hyperscale-cloud-service-provider-regions/2"
    ]


def test_a_synthesis_without_a_wan_still_serves_a_region_it_was_given(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_run_region("2", "1"))["name"] == "Provider D"


def test_a_region_of_an_unknown_synthesis_names_the_synthesis(served: Served) -> None:
    assert served(_get_run_region("3"))["error"] == MISSING


def test_an_unknown_region_of_a_synthesis_answers_404(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_run_region("1", "3"))["statusCode"] == 404


def test_an_unknown_region_of_a_synthesis_names_the_region(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_run_region("1", "3"))["error"] == MISSING_REGION


@pytest.mark.parametrize("region", ["#", "", "2/", "us-east-2"])
def test_a_region_id_that_is_not_a_number_asks_the_store_nothing(
    answer: Handler, store: SimpleNamespace, region: str
) -> None:
    assert (answer(_get_run_region("1", region))["statusCode"], store.gets) == (404, [])


def test_a_store_that_refuses_a_synthesis_s_region_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(_get_run_region())["error"]
    assert error == "Failed to read the hyperscale cloud service provider region"


OFF_NET = "/wan-syntheses/{synthesis}/off-net"
DULLES = {"id": 1, "municipality": "Dulles", "state": "VA", "country": "United States",
          "latitude": 38.9519, "longitude": -77.448}
RENO = {"id": 2, "municipality": "Reno", "state": "NV", "country": "United States",
        "latitude": 39.5296, "longitude": -119.8138}


def _get_off_net(synthesis: str = "1") -> Dict[str, Any]:
    return {**_get(OFF_NET), "pathParameters": {"synthesis": synthesis}}


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


FORCED_WAN_POPS = "/wan-syntheses/{synthesis}/forced-wan-pops"


def _get_forced_wan_pops(synthesis: str = "1") -> Dict[str, Any]:
    return {**_get(FORCED_WAN_POPS), "pathParameters": {"synthesis": synthesis}}


def test_the_forced_wan_pops_of_a_synthesis_answer_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_forced_wan_pops())["statusCode"] == 200


def test_the_forced_wan_pops_answer_as_named_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_forced_wan_pops()) == [
        {"id": 1, "name": "Ashburn, VA"}, {"id": 2, "name": "Cheyenne, WY"}
    ]


def test_a_synthesis_without_a_wan_still_answers_the_forced_wan_pops_it_was_given(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert [pop["name"] for pop in served(_get_forced_wan_pops("2"))] == ["Dayton, OH"]


def test_the_forced_wan_pops_are_read_from_under_the_synthesis_after_its_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_forced_wan_pops())
    assert (len(store.gets), store.queries[-1]["ExpressionAttributeValues"]) == (1, {
        ":pk": {"S": "wan-syntheses/1"}, ":prefix": {"S": "forced-wan-pops/"},
    })


def test_the_forced_wan_pops_of_an_unknown_synthesis_name_the_synthesis(served: Served) -> None:
    assert served(_get_forced_wan_pops("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "forced", "-1"])
def test_the_forced_wan_pops_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_forced_wan_pops(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_the_forced_wan_pops_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_forced_wan_pops())["error"] == "Failed to read the forced wan pops"


FORCED_CIRCUITS = "/wan-syntheses/{synthesis}/forced-circuits"


def _get_forced_circuits(synthesis: str = "1") -> Dict[str, Any]:
    return {**_get(FORCED_CIRCUITS), "pathParameters": {"synthesis": synthesis}}


def test_the_forced_circuits_of_a_synthesis_answer_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_forced_circuits())["statusCode"] == 200


def test_the_forced_circuits_answer_between_named_pops_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_forced_circuits()) == [
        {"id": 1, "source": "Ashburn, VA", "target": "Cheyenne, WY"},
        {"id": 2, "source": "Cheyenne, WY", "target": "Minot, ND"},
    ]


def test_a_synthesis_without_a_wan_still_answers_the_forced_circuits_it_was_given(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert [one["target"] for one in served(_get_forced_circuits("2"))] == ["Columbus, OH"]


def test_the_forced_circuits_are_read_from_under_the_synthesis_after_its_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_forced_circuits())
    assert (len(store.gets), store.queries[-1]["ExpressionAttributeValues"]) == (1, {
        ":pk": {"S": "wan-syntheses/1"}, ":prefix": {"S": "forced-circuits/"},
    })


def test_the_forced_circuits_of_an_unknown_synthesis_name_the_synthesis(served: Served) -> None:
    assert served(_get_forced_circuits("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "circuits", "-1"])
def test_the_forced_circuits_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_forced_circuits(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_the_forced_circuits_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_forced_circuits())["error"] == "Failed to read the forced circuits"
