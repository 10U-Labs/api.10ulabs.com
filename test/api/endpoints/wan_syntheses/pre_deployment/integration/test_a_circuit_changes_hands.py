from __future__ import annotations

import fixtures
from synthesizer.input_graph import segment_key
from synthesizer.model import SynthesisCircuit

_SHORTCUT_CITY = "t"
_SITES = ("a", "c")
ARTIFACTS = fixtures.synthesis_over_owned_fiber(
    _SITES,
    {
        ("a", "b"): (100.0, ("lumen",)),
        ("b", "c"): (100.0, ("lumen",)),
        ("c", "d"): (100.0, ("zayo",)),
        ("d", "a"): (100.0, ("zayo",)),
        ("a", _SHORTCUT_CITY): (10.0, ("lumen",)),
        (_SHORTCUT_CITY, "c"): (10.0, ("zayo",)),
    },
    2,
    transit_ids=("b", "d", _SHORTCUT_CITY),
)
_MESH = fixtures.mesh_circuits(ARTIFACTS)
_THE_SHORT_WAY = ("a", _SHORTCUT_CITY, "c")


def _circuits_at(site: str) -> list[SynthesisCircuit]:
    return [
        drawn_circuit
        for drawn_circuit in _MESH
        if site in (drawn_circuit.source, drawn_circuit.target)
    ]


def _owners_along(pop_ids: tuple[str, ...]) -> list[frozenset[str]]:
    return [
        ARTIFACTS.fiber_segments[segment_key(near, far)].carriers
        for near, far in zip(pop_ids, pop_ids[1:])
    ]


def test_the_short_way_that_changes_hands_is_drawn() -> None:
    assert _THE_SHORT_WAY in {drawn_circuit.pop_ids for drawn_circuit in _MESH}


def test_that_circuit_hands_off_from_one_carrier_to_the_next_at_the_pop_both_have() -> None:
    assert _owners_along(_THE_SHORT_WAY) == [frozenset({"lumen"}), frozenset({"zayo"})]


def test_every_drawn_circuit_runs_over_segments_each_of_which_a_carrier_owns() -> None:
    assert all(owners for drawn_circuit in _MESH for owners in _owners_along(drawn_circuit.pop_ids))


def test_every_site_still_holds_the_circuits_its_tenant_asked_for() -> None:
    assert all(len(_circuits_at(site)) == 2 for site in _SITES)


def test_the_ceiling_counts_the_circuits_that_change_hands() -> None:
    assert {
        str(row["id"]): row["ceiling"]
        for row in ARTIFACTS.validation["backbone_diverse_circuits_ceilings"]
    } == {"a": 3, "c": 3}


def test_the_synthesis_runs_the_miles_the_handoff_saves() -> None:
    assert ARTIFACTS.synthesis.metrics.physical_miles == 220.0
