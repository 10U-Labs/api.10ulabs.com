from __future__ import annotations

import fixtures

_SITES = ("a",)
_ASKED_FOR = 1
_SEGMENTS = {
    ("a", "north"): 100.0,
    ("north", "south"): 100.0,
    ("a", "south"): 200.0,
}
_TRANSIT = ("north", "south")
ARTIFACTS = fixtures.synthesis_over_segments(
    _SITES, _SEGMENTS, _ASKED_FOR, _TRANSIT,
    min_wan_pop_count=1, homing_degree=1,
)


def test_the_backbone_is_the_one_site() -> None:
    assert ARTIFACTS.synthesis.wan_pop_ids == ("a",)


def test_no_backbone_mesh_circuit_is_drawn() -> None:
    assert fixtures.mesh_circuits(ARTIFACTS) == []


def test_no_fiber_is_selected_for_a_site_with_no_peer_to_reach() -> None:
    assert ARTIFACTS.synthesis.fiber_segment_keys == set()


def test_the_floor_is_no_miles_at_all() -> None:
    assert ARTIFACTS.synthesis.metrics.backbone_lower_bound_miles == 0.0


def test_the_lone_site_is_credited_with_no_diverse_circuits() -> None:
    assert ARTIFACTS.validation["backbone_diverse_circuits_ceilings"] == [
        {"id": "a", "name": "a", "ceiling": 0, "target": 0}
    ]


def test_the_lone_site_is_not_reported_short_of_the_circuits_it_asked_for() -> None:
    assert ARTIFACTS.validation["backbone_mesh_independence_deficient"] == []
