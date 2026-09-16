from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest

from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
MISSING = "No such wan synthesis"


def _under(resource: str, synthesis: str, **member: str) -> Dict[str, Any]:
    parameters = {"id": synthesis, **member}
    return {"resource": resource, "httpMethod": "GET", "pathParameters": parameters}


SITES = "/wan-syntheses/{id}/sites"
WARREN = {"id": 1, "name": "F.E. Warren AFB", "municipality": "Cheyenne", "state": "WY",
          "country": "United States", "latitude": 41.1517, "longitude": -104.8678,
          "exempt_from_distance_constraint": False}
HILL = {"id": 2, "name": "Hill AFB", "municipality": "Layton", "state": "UT",
        "country": "United States", "latitude": 41.124, "longitude": -111.9731,
        "exempt_from_distance_constraint": False}


def _get_sites(synthesis: str = "1") -> Dict[str, Any]:
    return _under(SITES, synthesis)


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


SITE = "/wan-syntheses/{id}/sites/{site_id}"
MISSING_SITE = "No such site"


def _get_site(synthesis: str = "1", site: str = "2") -> Dict[str, Any]:
    return _under(SITE, synthesis, site_id=site)


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


RUN_REGIONS = "/wan-syntheses/{id}/hyperscale-cloud-service-provider-regions"
PROVIDER_A = {"id": 1, "name": "Provider A", "municipality": "Columbus", "state": "OH",
              "country": "United States", "latitude": 39.9612, "longitude": -82.9988}
PROVIDER_B = {"id": 2, "name": "Provider B", "municipality": "Boardman", "state": "OR",
              "country": "United States", "latitude": 45.8396, "longitude": -119.7006}


def _get_run_regions(synthesis: str = "1") -> Dict[str, Any]:
    return _under(RUN_REGIONS, synthesis)


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


RUN_REGION = "/wan-syntheses/{id}/hyperscale-cloud-service-provider-regions/{region_id}"
MISSING_REGION = "No such hyperscale cloud service provider region"


def _get_run_region(synthesis: str = "1", region: str = "2") -> Dict[str, Any]:
    return _under(RUN_REGION, synthesis, region_id=region)


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


@pytest.mark.parametrize("region", ["#", "", "2/", "Provider A"])
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


OFF_NET = "/wan-syntheses/{id}/off-net"
DULLES = {"id": 1, "municipality": "Dulles", "state": "VA", "country": "United States",
          "latitude": 38.9519, "longitude": -77.448}
RENO = {"id": 2, "municipality": "Reno", "state": "NV", "country": "United States",
        "latitude": 39.5296, "longitude": -119.8138}


def _get_off_net(synthesis: str = "1") -> Dict[str, Any]:
    return _under(OFF_NET, synthesis)


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


FORCED_WAN_POPS = "/wan-syntheses/{id}/forced-wan-pops"


def _get_forced_wan_pops(synthesis: str = "1") -> Dict[str, Any]:
    return _under(FORCED_WAN_POPS, synthesis)


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


FORCED_CIRCUITS = "/wan-syntheses/{id}/forced-circuits"


def _get_forced_circuits(synthesis: str = "1") -> Dict[str, Any]:
    return _under(FORCED_CIRCUITS, synthesis)


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


FORCED_HOMES = "/wan-syntheses/{id}/forced-homes"


def _get_forced_homes(synthesis: str = "1") -> Dict[str, Any]:
    return _under(FORCED_HOMES, synthesis)


def test_the_forced_homes_of_a_synthesis_answer_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_forced_homes())["statusCode"] == 200


def test_the_forced_homes_answer_from_a_named_site_to_a_named_pop_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_forced_homes()) == [
        {"id": 1, "source": "F.E. Warren AFB", "target": "Cheyenne, WY"},
        {"id": 2, "source": "Hill AFB", "target": "Salt Lake City, UT"},
    ]


def test_a_synthesis_without_a_wan_still_answers_the_forced_homes_it_was_given(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert [one["source"] for one in served(_get_forced_homes("2"))] == ["Wright-Patterson AFB"]


def test_the_forced_homes_are_read_from_under_the_synthesis_after_its_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_forced_homes())
    assert (len(store.gets), store.queries[-1]["ExpressionAttributeValues"]) == (1, {
        ":pk": {"S": "wan-syntheses/1"}, ":prefix": {"S": "forced-homes/"},
    })


def test_the_forced_homes_of_an_unknown_synthesis_name_the_synthesis(served: Served) -> None:
    assert served(_get_forced_homes("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "homes", "-1"])
def test_the_forced_homes_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_forced_homes(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_the_forced_homes_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_get_forced_homes())["error"] == "Failed to read the forced homes"


PROHIBITED_WAN_POPS = "/wan-syntheses/{id}/prohibited-wan-pops"


def _get_prohibited_wan_pops(synthesis: str = "1") -> Dict[str, Any]:
    return _under(PROHIBITED_WAN_POPS, synthesis)


def test_the_prohibited_wan_pops_of_a_synthesis_answer_200(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_get_prohibited_wan_pops())["statusCode"] == 200


def test_the_prohibited_wan_pops_answer_as_named_in_id_order(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_get_prohibited_wan_pops()) == [
        {"id": 1, "name": "Chicago, IL"}, {"id": 2, "name": "Los Angeles, CA"}
    ]


def test_a_synthesis_without_a_wan_still_answers_the_prohibited_wan_pops_it_was_given(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert [pop["name"] for pop in served(_get_prohibited_wan_pops("2"))] == ["Cleveland, OH"]


def test_the_prohibited_wan_pops_are_read_from_under_the_synthesis_after_its_record(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_get_prohibited_wan_pops())
    assert (len(store.gets), store.queries[-1]["ExpressionAttributeValues"]) == (1, {
        ":pk": {"S": "wan-syntheses/1"}, ":prefix": {"S": "prohibited-wan-pops/"},
    })


def test_the_prohibited_wan_pops_of_an_unknown_synthesis_name_the_synthesis(
    served: Served
) -> None:
    assert served(_get_prohibited_wan_pops("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "prohibited", "-1"])
def test_the_prohibited_wan_pops_of_an_id_that_is_not_a_number_answer_404(
    answer: Handler, synthesis: str
) -> None:
    assert answer(_get_prohibited_wan_pops(synthesis))["statusCode"] == 404


def test_a_store_that_refuses_the_prohibited_wan_pops_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    error = served(_get_prohibited_wan_pops())["error"]
    assert error == "Failed to read the prohibited wan pops"


PROHIBITED_CIRCUITS = "/wan-syntheses/{id}/prohibited-circuits"


def _get_prohibited_circuits(synthesis: str = "1") -> Dict[str, Any]:
    return _under(PROHIBITED_CIRCUITS, synthesis)


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


DEGREE_EXEMPT_WAN_POPS = "/wan-syntheses/{id}/degree-exempt-wan-pops"


def _get_degree_exempt_wan_pops(synthesis: str = "1") -> Dict[str, Any]:
    return _under(DEGREE_EXEMPT_WAN_POPS, synthesis)


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
