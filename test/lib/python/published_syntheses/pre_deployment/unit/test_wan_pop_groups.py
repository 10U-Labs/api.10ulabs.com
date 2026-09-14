from typing import Any, Dict

from published_syntheses import fiber_miles_run_over, wan_pop_groups

SPOTS = {"west": (40.0, -110.0), "hub": (40.0, -100.0), "east": (40.0, -90.0),
         "salt": (45.0, -112.0), "lake": (45.0, -111.0), "alone": (30.0, -95.0)}


def _wan_pop(name: str) -> Dict[str, Any]:
    latitude, longitude = SPOTS[name]
    return {"id": 1, "name": name, "latitude": latitude, "longitude": longitude}


def _segment(near: str, far: str, miles: float = 10.0) -> Dict[str, Any]:
    return {
        "a_latitude": SPOTS[near][0], "a_longitude": SPOTS[near][1],
        "z_latitude": SPOTS[far][0], "z_longitude": SPOTS[far][1], "distance_miles": miles,
    }


JOINED = [_segment("west", "hub"), _segment("hub", "east")]
SPLIT: Dict[str, Any] = {
    "wan_pops": [_wan_pop(name) for name in ("west", "east", "hub", "salt", "lake")],
    "fiber": [*JOINED, _segment("salt", "lake")],
}


def test_a_network_whose_fiber_joins_every_wan_pop_is_one_group() -> None:
    assert wan_pop_groups({"wan_pops": SPLIT["wan_pops"][:3], "fiber": JOINED}) == [
        ["east", "hub", "west"]
    ]


def test_wan_pops_the_fiber_leaves_in_two_groups_come_back_as_two_lists() -> None:
    assert wan_pop_groups(SPLIT) == [["east", "hub", "west"], ["lake", "salt"]]


def test_a_wan_pop_no_fiber_touches_at_all_is_a_group_of_one() -> None:
    assert wan_pop_groups({
        "wan_pops": [*SPLIT["wan_pops"][:3], _wan_pop("alone")],
        "fiber": JOINED,
    }) == [["alone"], ["east", "hub", "west"]]


def test_a_run_with_no_published_backbone_has_no_group() -> None:
    assert not wan_pop_groups({"wan_pops": [], "fiber": []})


def test_the_miles_are_the_carrier_fiber_the_wan_runs_over() -> None:
    fiber = [_segment("west", "hub", 120.5), _segment("hub", "east", 240.25)]
    assert fiber_miles_run_over({"fiber": fiber}) == 360.75


def test_a_wan_carrying_no_circuits_runs_over_no_fiber() -> None:
    assert fiber_miles_run_over({"fiber": []}) == 0
