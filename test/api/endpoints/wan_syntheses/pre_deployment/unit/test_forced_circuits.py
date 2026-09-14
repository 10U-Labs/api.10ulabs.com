from __future__ import annotations

import pytest

import fixtures
from synthesizer.forced import (
    apply_forced_homes,
    forced_backbone_pairs,
    removed_backbone_pairs,
)
from synthesizer.overrides import resolve_forced_circuits
from synthesizer.model import ForcedCircuits, NamedCircuit, OperatorCircuits
from synthesizer.input_graph import segment_key

pop = fixtures.carrier_pop
access = fixtures.tenant_site

SITES = [pop("P0"), pop("P1"), access("A1")]


def test_backbone_circuit_resolves_to_a_segment_key() -> None:
    circuits = resolve_forced_circuits(
        OperatorCircuits(backbone=(NamedCircuit("P0", "P1"),)), SITES, {"P0", "P1"}
    )
    assert circuits.backbone == frozenset({segment_key("P0", "P1")})


def test_forced_home_resolves_to_an_ordered_pair() -> None:
    circuits = resolve_forced_circuits(
        OperatorCircuits(homes=(NamedCircuit("A1", "P1"),)), SITES, {"P1"}
    )
    assert circuits.homes == frozenset({("A1", "P1")})


def test_excluded_backbone_resolves_to_a_removed_pair() -> None:
    circuits = resolve_forced_circuits(
        OperatorCircuits(removed_backbone=(NamedCircuit("P0", "P1"),)), SITES, {"P0", "P1"}
    )
    assert circuits.removed_backbone == frozenset({segment_key("P0", "P1")})


def test_excluded_wan_pop_endpoint_need_not_be_forced() -> None:
    circuits = resolve_forced_circuits(
        OperatorCircuits(removed_backbone=(NamedCircuit("P0", "P1"),)), SITES, set()
    )
    assert circuits.removed_backbone == frozenset({segment_key("P0", "P1")})


def test_excluded_backbone_unknown_endpoint_is_rejected() -> None:
    with pytest.raises(ValueError):
        resolve_forced_circuits(
            OperatorCircuits(removed_backbone=(NamedCircuit("Nowhere", "P1"),)), SITES, set()
        )


def test_removed_backbone_pairs_keeps_only_in_set_pairs() -> None:
    circuits = ForcedCircuits(
        removed_backbone=frozenset({segment_key("P0", "P1"), segment_key("P0", "P9")})
    )
    assert removed_backbone_pairs({"P0", "P1"}, circuits) == frozenset({segment_key("P0", "P1")})


def test_forced_backbone_pairs_keeps_only_in_set_pairs() -> None:
    circuits = ForcedCircuits(
        backbone=frozenset({segment_key("P0", "P1"), segment_key("P0", "P9")})
    )
    assert forced_backbone_pairs({"P0", "P1"}, circuits) == frozenset({segment_key("P0", "P1")})


def test_unknown_backbone_endpoint_is_rejected() -> None:
    with pytest.raises(ValueError, match="forced-circuit"):
        resolve_forced_circuits(
            OperatorCircuits(backbone=(NamedCircuit("Nowhere", "P1"),)), SITES, {"P1"}
        )


def test_backbone_endpoint_not_forced_is_rejected() -> None:
    with pytest.raises(ValueError, match="forced-circuit"):
        resolve_forced_circuits(
            OperatorCircuits(backbone=(NamedCircuit("P0", "P1"),)), SITES, {"P0"}
        )


def test_forced_home_target_not_forced_names_the_home_list() -> None:
    with pytest.raises(ValueError, match="forced-home"):
        resolve_forced_circuits(
            OperatorCircuits(homes=(NamedCircuit("A1", "P1"),)), SITES, set()
        )


def test_forced_home_target_off_the_carrier_graph_names_the_home_list() -> None:
    with pytest.raises(ValueError, match="forced-home"):
        resolve_forced_circuits(
            OperatorCircuits(homes=(NamedCircuit("A1", "Nowhere"),)), SITES, {"P1"}
        )


def test_forced_home_source_that_is_not_demand_is_rejected() -> None:
    with pytest.raises(ValueError):
        resolve_forced_circuits(
            OperatorCircuits(homes=(NamedCircuit("Nope", "P1"),)), SITES, {"P1"}
        )


def test_a_mesh_pair_is_not_read_as_a_home() -> None:
    circuits = resolve_forced_circuits(
        OperatorCircuits(backbone=(NamedCircuit("P0", "P1"),)), SITES, {"P0", "P1"}
    )
    assert circuits.homes == frozenset()


def test_no_forced_circuit_returns_homes_unchanged() -> None:
    pop_by_id = {"P0": pop("P0", 40.0, -100.0), "P1": pop("P1", 50.0, -100.0)}
    homes = apply_forced_homes(
        access("A1", 40.0, -100.0), ["P0", "P1"], ForcedCircuits(), pop_by_id, 2
    )
    assert homes == ["P0", "P1"]


def test_forced_access_home_is_pinned_over_a_nearer_facility() -> None:
    circuits = ForcedCircuits(homes=frozenset({("A1", "P3")}))
    pop_by_id = {
        "P0": pop("P0", 40.0, -100.1),
        "P1": pop("P1", 50.0, -100.0),
        "P3": pop("P3", 41.0, -99.0),
    }
    homes = apply_forced_homes(
        access("A1", 40.0, -100.0), ["P0", "P1"], circuits, pop_by_id, 2
    )
    assert set(homes) == {"P3", "P0"}
