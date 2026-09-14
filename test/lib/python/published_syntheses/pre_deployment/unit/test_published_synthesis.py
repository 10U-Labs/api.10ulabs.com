from typing import Any, Dict, List

import pytest

from published_syntheses import homed_rows, published_synthesis, wan_pop_names

CONFIG: Dict[str, Any] = {
    "backbone": {
        "coverage_target_miles": 200,
        "wan_pop_count": {"min": 2, "max": 6},
        "number_of_diverse_circuits": 2,
        "forced": {
            "circuits": [{"source": "Ashburn, VA", "target": "New York, NY"}],
            "wan_pops": ["Ashburn, VA"],
        },
    },
    "homing": {"degree": 2},
}
ASHBURN = {"id": 1, "name": "Ashburn, VA", "latitude": 39.0, "longitude": -77.5}
SITE = {"id": 1, "name": "Site", "latitude": 38.9, "longitude": -77.0}
REGION = {"id": 1, "name": "Provider A", "latitude": 39.0, "longitude": -78.0}
CIRCUIT = {"id": 1, "source": 1, "target": 2, "distance_miles": 240.0, "route": ["a", "b"]}
HOMING = {"id": 1, "source_id": 1, "homing_kind": "tenant_to_backbone", "target": 1}
SEGMENT = {"id": 1, "distance_miles": 240.0}
SUCCEEDED = {
    "id": 3, "label": "daf", "status": "success", "coverage": {"target_miles": 200, "met": True},
    "backbone_lower_bound_miles": 1250.0,
}
LISTED = [{"id": 1, "label": "daf"}, {"id": 2, "label": "dow"}, {"id": 3, "label": "daf"}]


def _reading(bodies: Dict[str, Any]) -> Any:
    def read(path: str) -> Any:
        return bodies[path]
    return read


@pytest.fixture(name="served")
def served_fixture() -> Dict[str, Any]:
    return {
        "/wan-syntheses": LISTED,
        "/wan-syntheses/3": SUCCEEDED,
        "/wan-syntheses/3/wan-pops": [ASHBURN],
        "/wan-syntheses/3/backbone-circuits": [CIRCUIT],
        "/wan-syntheses/3/homing-circuits": [HOMING],
        "/wan-syntheses/3/fiber-segments": [SEGMENT],
        "/wan-syntheses/3/sites": [SITE],
        "/wan-syntheses/3/hyperscale-cloud-service-provider-regions": [REGION],
    }


def test_a_published_network_is_read_beside_the_demands_its_config_makes(
    served: Dict[str, Any]
) -> None:
    assert published_synthesis(_reading(served), "daf", CONFIG) == {
        "label": "daf",
        "id": 3,
        "target_miles": 200,
        "number_of_diverse_circuits": 2,
        "homing_degree": 2,
        "max_wan_pop_count": 6,
        "forced": ["Ashburn, VA"],
        "forced_circuits": [{"source": "Ashburn, VA", "target": "New York, NY"}],
        "status": SUCCEEDED,
        "lower_bound_miles": 1250.0,
        "wan_pops": [ASHBURN],
        "sites": [SITE],
        "regions": [REGION],
        "circuits": [CIRCUIT],
        "homings": [HOMING],
        "fiber": [SEGMENT],
    }


def test_the_latest_run_of_a_label_is_the_one_read(served: Dict[str, Any]) -> None:
    assert published_synthesis(_reading(served), "daf", CONFIG)["id"] == 3


def test_a_run_that_has_not_published_is_read_with_its_inputs_and_no_network(
    served: Dict[str, Any]
) -> None:
    served["/wan-syntheses/3"] = {"id": 3, "label": "daf", "status": "synthesizing"}
    synthesis = published_synthesis(_reading(served), "daf", CONFIG)
    assert [
        synthesis["sites"], synthesis["regions"], synthesis["wan_pops"], synthesis["circuits"],
        synthesis["homings"], synthesis["fiber"], synthesis["lower_bound_miles"],
    ] == [[SITE], [REGION], [], [], [], [], None]


def test_a_run_that_failed_is_read_as_what_its_record_says_went_wrong(
    served: Dict[str, Any]
) -> None:
    served["/wan-syntheses/3"] = {"id": 3, "label": "daf", "status": "fail", "reason": "split"}
    synthesis = published_synthesis(_reading(served), "daf", CONFIG)
    assert (synthesis["status"]["reason"], synthesis["wan_pops"]) == ("split", [])


def test_a_label_no_run_carries_is_read_with_no_record(served: Dict[str, Any]) -> None:
    synthesis = published_synthesis(_reading(served), "f-35", CONFIG)
    assert (synthesis["id"], synthesis["status"], synthesis["sites"]) == (None, {}, [])


def test_a_config_forcing_nothing_forces_nothing() -> None:
    config = {"backbone": {**CONFIG["backbone"], "forced": {}}, "homing": {"degree": 2}}
    synthesis = published_synthesis(_reading({"/wan-syntheses": []}), "daf", config)
    assert (synthesis["forced"], synthesis["forced_circuits"]) == ([], [])


def test_the_homed_rows_are_the_sites_then_the_regions() -> None:
    assert homed_rows({"sites": [SITE], "regions": [REGION]}) == [SITE, REGION]


def test_the_wan_pops_are_named_by_id() -> None:
    names: List[Dict[str, Any]] = [ASHBURN, {"id": 2, "name": "New York, NY"}]
    assert wan_pop_names({"wan_pops": names}) == {1: "Ashburn, VA", 2: "New York, NY"}
