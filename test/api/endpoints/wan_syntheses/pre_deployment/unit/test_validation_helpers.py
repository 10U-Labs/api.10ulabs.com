from __future__ import annotations

import fixtures
import pytest

from synthesizer.input_graph import segment_key
from synthesizer.model import Homings, HomingCircuit, Synthesis, SynthesisMetrics, MeshRequirements
from synthesizer.validation import (
    backbone_mesh_deficient,
    backbone_mesh_independence_deficient,
    homes_by_site,
    synthesis_site_pairs,
    included_site_ids,
    diverse_circuit_count,
    neighbor_degrees,
)


def make_synthesis(
    physical_pairs: list[tuple[str, str]],
    *,
    wan_pop_ids: tuple[str, ...] = (),
    transit_ids: tuple[str, ...] = (),
    homing_circuits: list[HomingCircuit] | None = None,
    provider_homing_circuits: list[HomingCircuit] | None = None,
) -> Synthesis:
    return Synthesis(
        wan_pop_ids=wan_pop_ids,
        transit_ids=transit_ids,
        homings=Homings(homing_circuits or [], provider_homing_circuits or []),
        fiber_segment_keys={segment_key(a, b) for a, b in physical_pairs},
        drawn_circuits=[],
        metrics=SynthesisMetrics(0.0, 0.0, 0.0),
    )


meshed_synthesis = fixtures.meshed_backbone_synthesis


def test_included_site_ids_covers_homing_endpoints() -> None:
    synthesis = make_synthesis([("a", "b")], homing_circuits=[HomingCircuit("s", "a", 1.0)])
    assert included_site_ids(synthesis) == {"a", "b", "s"}


def test_included_site_ids_covers_a_provider_regions_homing_endpoints() -> None:
    synthesis = make_synthesis(
        [], provider_homing_circuits=[HomingCircuit("r", "a", 1.0)]
    )
    assert included_site_ids(synthesis) == {"a", "r"}


def test_homes_by_site_groups_a_provider_region_beside_a_tenant_site() -> None:
    synthesis = make_synthesis(
        [],
        homing_circuits=[HomingCircuit("s", "a", 1.0)],
        provider_homing_circuits=[HomingCircuit("r", "a", 1.0)],
    )
    assert homes_by_site(synthesis) == {"s": {"a"}, "r": {"a"}}


def test_included_site_ids_covers_the_tier_ids() -> None:
    synthesis = make_synthesis([], wan_pop_ids=("b",), transit_ids=("t",))
    assert included_site_ids(synthesis) == {"b", "t"}


def test_synthesis_site_pairs_merge_homing_and_physical() -> None:
    synthesis = make_synthesis([("a", "b")], homing_circuits=[HomingCircuit("s", "a", 1.0)])
    assert synthesis_site_pairs(synthesis) == {segment_key("a", "b"), segment_key("s", "a")}


def test_neighbor_degrees_counts_distinct_neighbors() -> None:
    degrees = neighbor_degrees({"a", "b", "c"}, {("a", "b"), ("b", "c")})
    assert degrees == {"a": 1, "b": 2, "c": 1}


def test_neighbor_degrees_ignores_external_endpoints() -> None:
    degrees = neighbor_degrees({"a", "b"}, {("a", "b"), ("a", "z")})
    assert degrees == {"a": 1, "b": 1}


def test_homes_by_site_groups_targets_per_source() -> None:
    synthesis = make_synthesis(
        [], homing_circuits=[HomingCircuit("s", "a", 1.0), HomingCircuit("s", "b", 1.0)]
    )
    assert homes_by_site(synthesis) == {"s": {"a", "b"}}


_SHARED_EGRESS = meshed_synthesis(
    fixtures.SHARED_TRANSIT_CIRCUITS, fixtures.SHARED_TRANSIT_WAN_POPS
)
_DIVERSE_EGRESS = meshed_synthesis(
    fixtures.DIVERSE_TRANSIT_CIRCUITS, fixtures.SHARED_TRANSIT_WAN_POPS
)
_MESH_SITES = fixtures.carrier_pops_by_id("abcxy")


@pytest.mark.parametrize("degree", [2, 3, 4])
def test_diverse_circuit_count_counts_every_city_disjoint_circuit(degree: int) -> None:
    peers = "bcde"[:degree]
    synthesis = meshed_synthesis(
        [("a", f"x{peer}", peer) for peer in peers], ("a", *peers)
    )
    assert diverse_circuit_count(synthesis.drawn_circuits, "a") == degree


def test_diverse_circuit_count_counts_circuits_sharing_a_transit_city_once() -> None:
    assert diverse_circuit_count(_SHARED_EGRESS.drawn_circuits, "a") == 1


def test_diverse_circuit_count_counts_a_diverse_pair_as_two() -> None:
    assert diverse_circuit_count(_DIVERSE_EGRESS.drawn_circuits, "a") == 2


def test_diverse_circuit_count_of_a_wan_pop_with_no_circuits_is_zero() -> None:
    assert diverse_circuit_count(meshed_synthesis([], ("a",)).drawn_circuits, "a") == 0


def test_diverse_circuit_count_counts_two_circuits_to_the_only_peer_as_two() -> None:
    synthesis = meshed_synthesis([("a", "x", "b"), ("a", "y", "b")], ("a", "b"))
    assert diverse_circuit_count(synthesis.drawn_circuits, "a") == 2


def test_diverse_circuit_count_counts_a_circuit_crossing_a_peer_with_that_peer_once() -> None:
    synthesis = meshed_synthesis([("a", "b"), ("a", "b", "c")], ("a", "b", "c"))
    assert diverse_circuit_count(synthesis.drawn_circuits, "a") == 1


_MESH_DEGREES = {"a": 1, "b": 2, "c": 2, "d": 2}
_MESH_WAN_POPS = ("a", "b", "c", "d")


def test_mesh_deficient_names_the_wan_pop_below_the_degree() -> None:
    sites = fixtures.carrier_pops_by_id("abcd")
    assert backbone_mesh_deficient(_MESH_WAN_POPS, _MESH_DEGREES, sites, MeshRequirements(2)) == [
        {"id": "a", "name": "a", "degree": 1}
    ]


def test_mesh_deficient_leaves_out_an_exempt_node() -> None:
    sites = fixtures.carrier_pops_by_id("abcd")
    assert backbone_mesh_deficient(
        _MESH_WAN_POPS, _MESH_DEGREES, sites, MeshRequirements(2, frozenset({"a"}))
    ) == []


def test_mesh_deficient_still_names_a_wan_pop_that_is_not_exempt() -> None:
    sites = fixtures.carrier_pops_by_id("abcd")
    assert backbone_mesh_deficient(
        _MESH_WAN_POPS, _MESH_DEGREES, sites, MeshRequirements(2, frozenset({"b"}))
    ) == [{"id": "a", "name": "a", "degree": 1}]


def test_mesh_deficient_holds_a_capped_wan_pop_to_its_ceiling() -> None:
    sites = fixtures.carrier_pops_by_id("abcd")
    assert backbone_mesh_deficient(
        _MESH_WAN_POPS, _MESH_DEGREES, sites, MeshRequirements(2, ceilings={"a": 1})
    ) == []


def test_independence_deficient_names_the_wan_pop_below_the_degree() -> None:
    assert backbone_mesh_independence_deficient(
        _SHARED_EGRESS, _MESH_SITES, MeshRequirements(2)
    ) == [
        {"id": "a", "name": "a", "independent_degree": 1}
    ]


def test_independence_deficient_leaves_out_an_exempt_node() -> None:
    assert backbone_mesh_independence_deficient(
        _SHARED_EGRESS, _MESH_SITES, MeshRequirements(2, frozenset({"a"}))
    ) == []


def test_independence_deficient_still_names_a_wan_pop_that_is_not_exempt() -> None:
    assert backbone_mesh_independence_deficient(
        _SHARED_EGRESS, _MESH_SITES, MeshRequirements(2, frozenset({"b"}))
    ) == [{"id": "a", "name": "a", "independent_degree": 1}]


def test_independence_deficient_passes_a_diversely_drawn_mesh() -> None:
    assert backbone_mesh_independence_deficient(
        _DIVERSE_EGRESS, _MESH_SITES, MeshRequirements(2)
    ) == []


def test_independence_deficient_holds_a_capped_wan_pop_to_its_ceiling() -> None:
    assert backbone_mesh_independence_deficient(
        _SHARED_EGRESS, _MESH_SITES, MeshRequirements(2, ceilings={"a": 1})
    ) == []


def test_independence_deficient_still_names_a_wan_pop_under_its_own_ceiling() -> None:
    assert backbone_mesh_independence_deficient(
        _SHARED_EGRESS, _MESH_SITES, MeshRequirements(2, ceilings={"a": 2})
    ) == [{"id": "a", "name": "a", "independent_degree": 1}]


@pytest.mark.parametrize("degree", [2, 3, 4])
def test_independence_deficient_still_asks_a_backbone_no_larger_than_the_degree(
    degree: int,
) -> None:
    backbone = "abcd"[:degree]
    synthesis = meshed_synthesis([], tuple(backbone))
    sites = fixtures.carrier_pops_by_id(backbone)
    assert [
        row["id"]
        for row in backbone_mesh_independence_deficient(
            synthesis, sites, MeshRequirements(degree)
        )
    ] == list(backbone)
