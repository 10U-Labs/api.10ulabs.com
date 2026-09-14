from types import ModuleType
from typing import Any, Callable, Dict, List

import pytest

INPUTS = {
    "wan_pop_count": {"M": {"min": {"N": "3"}, "max": {"N": "6"}}},
    "backbone_number_of_diverse_circuits": {"N": "3"},
    "homing_degree": {"N": "2"},
    "convergence_promotion": {"BOOL": False},
    "knobs": {"M": {"coverage_target_miles": {"N": "1200"}}},
    "settings": {"M": {
        "compass_sector_count": {"N": "8"}, "wan_pop_search_memory_share": {"N": "0.6"},
    }},
}


@pytest.fixture
def handler(endpoint: Callable[[str], ModuleType]) -> ModuleType:
    return endpoint("wan_syntheses")


@pytest.fixture
def syntheses() -> List[Dict[str, Any]]:
    return [
        {"PK": {"S": "wan-syntheses"}, "SK": {"S": "#"}, "next": {"N": "3"}},
        {"PK": {"S": "wan-syntheses"}, "SK": {"S": "2"}, "label": {"S": "daf"}, **INPUTS,
         "status": {"S": "fail"}, "reason": {"S": "No 2-vertex-connected backbone"}},
        {"PK": {"S": "wan-syntheses"}, "SK": {"S": "1"}, "label": {"S": "minuteman"}, **INPUTS,
         "status": {"S": "success"},
         "coverage": {"M": {"delivered_miles": {"N": "1250.5"}, "target_miles": {"N": "1200"}}},
         "fiber_miles": {"N": "4321.125"}, "backbone_lower_bound_miles": {"N": "3900"},
         "homing_miles": {"M": {"tenant": {"N": "210.25"}, "provider": {"N": "80"}}},
         "diverse_circuits": {"M": {"number_of_diverse_circuits": {"N": "3"},
                                    "ceilings": {"L": [{"N": "3"}, {"N": "2"}]}}}},
        {"PK": {"S": "wan-syntheses/1"}, "SK": {"S": "wan-pops/2"}, "name": {"S": "Cheyenne, WY"},
         "municipality": {"S": "Cheyenne"}, "state": {"S": "WY"}, "country": {"S": "US"},
         "latitude": {"N": "41.14"}, "longitude": {"N": "-104.8202"}, "carrier": {"S": "lumen"}},
        {"PK": {"S": "wan-syntheses/1"}, "SK": {"S": "wan-pops/1"}, "name": {"S": "Ashburn, VA"},
         "municipality": {"S": "Ashburn"}, "state": {"S": "VA"}, "country": {"S": "US"},
         "latitude": {"N": "39.0438"}, "longitude": {"N": "-77.4874"}, "carrier": {"S": "zayo"}},
        {"PK": {"S": "wan-syntheses/1"}, "SK": {"S": "backbone-circuits/2"},
         "source": {"N": "2"}, "target": {"N": "1"},
         "route": {"L": [{"S": "Cheyenne, WY"}, {"S": "Omaha, NE"}, {"S": "Ashburn, VA"}]},
         "distance_miles": {"N": "1612.5"}, "reason": {"S": "circuit_for_target"},
         "requested_by": {"L": [{"S": "Minot, ND"}]}},
        {"PK": {"S": "wan-syntheses/1"}, "SK": {"S": "backbone-circuits/1"},
         "source": {"N": "1"}, "target": {"N": "2"},
         "route": {"L": [{"S": "Ashburn, VA"}, {"S": "Chicago, IL"}, {"S": "Cheyenne, WY"}]},
         "distance_miles": {"N": "1480"}, "reason": {"S": "circuit_for_target"},
         "requested_by": {"L": []}},
        {"PK": {"S": "wan-syntheses/1"}, "SK": {"S": "homing-circuits/2"},
         "source_id": {"N": "1"}, "homing_kind": {"S": "provider_to_backbone"},
         "target": {"N": "1"}, "route": {"L": [{"S": "Columbus, OH"}, {"S": "Ashburn, VA"}]},
         "distance_miles": {"N": "331.25"}},
        {"PK": {"S": "wan-syntheses/1"}, "SK": {"S": "homing-circuits/1"},
         "source_id": {"N": "1"}, "homing_kind": {"S": "tenant_to_backbone"},
         "target": {"N": "2"}, "route": {"L": [{"S": "Minot, ND"}, {"S": "Cheyenne, WY"}]},
         "distance_miles": {"N": "590"}},
        {"PK": {"S": "wan-syntheses/1"}, "SK": {"S": "fiber-segments/2"}, "carrier": {"S": "lumen"},
         "a_municipality": {"S": "Chicago"}, "a_state": {"S": "IL"},
         "a_latitude": {"N": "41.8781"}, "a_longitude": {"N": "-87.6298"},
         "z_municipality": {"S": "Cheyenne"}, "z_state": {"S": "WY"},
         "z_latitude": {"N": "41.14"}, "z_longitude": {"N": "-104.8202"},
         "distance_miles": {"N": "880.5"}, "submarine": {"BOOL": False}},
        {"PK": {"S": "wan-syntheses/1"}, "SK": {"S": "fiber-segments/1"}, "carrier": {"S": "zayo"},
         "a_municipality": {"S": "Ashburn"}, "a_state": {"S": "VA"},
         "a_latitude": {"N": "39.0438"}, "a_longitude": {"N": "-77.4874"},
         "z_municipality": {"S": "Chicago"}, "z_state": {"S": "IL"},
         "z_latitude": {"N": "41.8781"}, "z_longitude": {"N": "-87.6298"},
         "distance_miles": {"N": "599.5"}, "submarine": {"BOOL": False}},
        {"PK": {"S": "wan-syntheses/1"}, "SK": {"S": "sites/2"}, "name": {"S": "Hill AFB"},
         "municipality": {"S": "Layton"}, "state": {"S": "UT"}, "country": {"S": "United States"},
         "latitude": {"N": "41.124"}, "longitude": {"N": "-111.9731"},
         "exempt_from_distance_constraint": {"BOOL": False}},
        {"PK": {"S": "wan-syntheses/1"}, "SK": {"S": "sites/1"}, "name": {"S": "F.E. Warren AFB"},
         "municipality": {"S": "Cheyenne"}, "state": {"S": "WY"}, "country": {"S": "United States"},
         "latitude": {"N": "41.1517"}, "longitude": {"N": "-104.8678"},
         "exempt_from_distance_constraint": {"BOOL": False}},
        {"PK": {"S": "wan-syntheses/2"}, "SK": {"S": "sites/1"},
         "name": {"S": "Wright-Patterson AFB"}, "municipality": {"S": "Dayton"},
         "state": {"S": "OH"}, "country": {"S": "United States"},
         "latitude": {"N": "39.8261"}, "longitude": {"N": "-84.0483"},
         "exempt_from_distance_constraint": {"BOOL": True}},
    ]
