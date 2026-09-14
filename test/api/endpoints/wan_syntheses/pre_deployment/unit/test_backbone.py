from __future__ import annotations

import fixtures
from synthesizer.input_graph import FiberSegment, segment_key
from synthesizer.model import (
    CIRCUIT_FOR_PIN,
    CIRCUIT_FOR_RELIEF,
    CIRCUIT_FOR_TARGET,
    SynthesisCircuit,
)
from synthesizer.backbone import (
    WanPopConstraints,
    BackboneMesh,
    _needed,
    backbone_mesh,
    miles_along,
)
from synthesizer.survivable import FiberInputs, select_fiber
from synthesizer.synthesize import all_pairs_shortest
from synthesizer.graphs import (
    articulation_points,
    build_adjacency,
    fiber_segments_along,
)

pop = fixtures.carrier_pop
physical = fixtures.fiber_segments_from


def _distances(
    fiber: dict[tuple[str, str], FiberSegment],
) -> dict[str, dict[str, float]]:
    cities = sorted({city for pair in fiber for city in pair})
    distances, _predecessors = all_pairs_shortest(
        [pop(city) for city in cities], build_adjacency(fiber)
    )
    return distances


def _drawn(
    sites: tuple[str, ...],
    fiber: dict[tuple[str, str], FiberSegment],
    constraints: WanPopConstraints,
) -> BackboneMesh:
    return backbone_mesh(sites, _distances(fiber), fiber, constraints)


def _selected(
    fiber: dict[tuple[str, str], FiberSegment],
    sites: tuple[str, ...],
    constraints: WanPopConstraints,
) -> frozenset[tuple[str, str]]:
    return select_fiber(FiberInputs(
        sites, fiber, constraints.number_of_diverse_circuits
    )).segments


def _asking(asked_for: int = 2) -> WanPopConstraints:
    return WanPopConstraints(number_of_diverse_circuits=asked_for)


def _pairs(mesh: BackboneMesh) -> set[tuple[str, str]]:
    return {
        segment_key(drawn_circuit.source, drawn_circuit.target)
        for drawn_circuit in mesh.circuits
    }


def _mesh_miles(mesh: BackboneMesh) -> float:
    return sum(drawn_circuit.distance_miles for drawn_circuit in mesh.circuits)


def _cut(mesh: BackboneMesh) -> set[str]:
    segments = {
        key
        for drawn_circuit in mesh.circuits
        for key in fiber_segments_along(drawn_circuit.pop_ids)
    }
    return articulation_points({city for pair in segments for city in pair}, segments)


def _joining(mesh: BackboneMesh, left: str, right: str) -> SynthesisCircuit:
    return next(
        drawn_circuit
        for drawn_circuit in mesh.circuits
        if segment_key(drawn_circuit.source, drawn_circuit.target) == segment_key(left, right)
    )


_SQUARE_SITES = ("w", "x", "y", "z")
_SQUARE_FIBER = physical({
    ("w", "x"): 100.0, ("x", "y"): 100.0, ("y", "z"): 100.0, ("z", "w"): 100.0,
    ("w", "y"): 250.0, ("x", "z"): 250.0,
})
_TWO_DIVERSE_CIRCUITS = WanPopConstraints(number_of_diverse_circuits=2)
_SQUARE = _drawn(_SQUARE_SITES, _SQUARE_FIBER, _TWO_DIVERSE_CIRCUITS)


def test_the_square_is_drawn_with_one_circuit_a_pair_round_the_ring() -> None:
    assert _pairs(_SQUARE) == {
        segment_key("w", "x"), segment_key("x", "y"), segment_key("y", "z"), segment_key("z", "w"),
    }


def test_the_square_selects_neither_of_the_chords() -> None:
    assert _SQUARE_FIBER.keys() - {
        segment_key(*pair)
        for drawn_circuit in _SQUARE.circuits
        for pair in zip(drawn_circuit.pop_ids, drawn_circuit.pop_ids[1:])
    } == {segment_key("w", "y"), segment_key("x", "z")}


def test_the_square_runs_the_fewest_miles_its_fiber_allows() -> None:
    assert _mesh_miles(_SQUARE) == 400.0


def test_the_square_publishes_the_floor_it_was_judged_against() -> None:
    assert round(_SQUARE.lower_bound_miles, 3) == 400.0


def test_the_square_runs_no_further_than_twice_the_floor() -> None:
    assert _mesh_miles(_SQUARE) <= 2 * _SQUARE.lower_bound_miles


def test_every_circuit_the_square_draws_says_a_site_reached_for_it() -> None:
    assert {drawn_circuit.reason for drawn_circuit in _SQUARE.circuits} == {CIRCUIT_FOR_TARGET}


def test_a_circuit_names_both_of_the_sites_that_reached_for_it() -> None:
    assert _joining(_SQUARE, "w", "x").requested_by == ("w", "x")


def test_no_circuit_the_square_holds_could_be_taken_back_out() -> None:
    assert _needed(_SQUARE.circuits, _SQUARE_SITES, 2) == _SQUARE.circuits


_EGRESS_SITES = ("hub", "p", "q")
_EGRESS_FIBER = physical({
    ("hub", "m"): 10.0, ("m", "p"): 10.0, ("m", "q"): 10.0,
    ("hub", "n"): 11.0, ("n", "q"): 11.0, ("p", "q"): 10.0,
})
_EGRESS = _drawn(_EGRESS_SITES, _EGRESS_FIBER, _TWO_DIVERSE_CIRCUITS)


def test_the_longer_circuit_round_a_shared_city_is_the_one_drawn() -> None:
    assert ("hub", "n", "q") in {drawn_circuit.pop_ids for drawn_circuit in _EGRESS.circuits}


def test_the_shorter_circuit_round_that_shared_city_is_not_selected_at_all() -> None:
    assert segment_key("m", "q") not in {
        segment_key(*pair)
        for drawn_circuit in _EGRESS.circuits
        for pair in zip(drawn_circuit.pop_ids, drawn_circuit.pop_ids[1:])
    }


def test_the_shared_egress_graph_joins_all_three_pairs_once() -> None:
    assert len(_EGRESS.circuits) == 3


def test_the_shared_egress_synthesis_runs_the_miles_its_five_segments_cost() -> None:
    assert _mesh_miles(_EGRESS) == 52.0


def test_no_circuit_the_shared_egress_synthesis_holds_could_be_taken_back_out() -> None:
    assert _needed(_EGRESS.circuits, _EGRESS_SITES, 2) == _EGRESS.circuits


_LOBE_SITES = ("a", "b", "c", "d")
_LOBE_LOBES: dict[tuple[str, str], tuple[float, tuple[str, ...]]] = {
    ("a", "b"): (10.0, ("lumen",)),
    ("a", "mid"): (15.0, ("lumen",)),
    ("b", "mid"): (5.0, ("lumen",)),
    ("c", "d"): (10.0, ("lumen",)),
    ("c", "mid"): (5.0, ("lumen",)),
    ("d", "mid"): (15.0, ("lumen",)),
}
_LOBE_FIBER = fixtures.carrier_fiber_segments({
    **_LOBE_LOBES, ("b", "w"): (20.0, ("zayo",)), ("w", "c"): (20.0, ("zayo",)),
})
_TWO_LOBES = _drawn(_LOBE_SITES, _LOBE_FIBER, _asking())
_BOWTIE_FIBER = fixtures.carrier_fiber_segments(_LOBE_LOBES)
_BOWTIE = _drawn(_LOBE_SITES, _BOWTIE_FIBER, _asking())
_ONE_WAY_OUT_LOBES = _drawn(_LOBE_SITES, _LOBE_FIBER, _asking(1))


def test_a_city_every_drawn_circuit_crosses_is_given_a_circuit_round_it() -> None:
    assert _cut(_TWO_LOBES) == set()


def test_the_circuit_drawn_round_that_city_runs_over_the_fiber_that_goes_round_it() -> None:
    assert [
        drawn_circuit.pop_ids
        for drawn_circuit in _TWO_LOBES.circuits
        if segment_key("b", "w") in fiber_segments_along(drawn_circuit.pop_ids)
    ] == [("b", "w", "c")]


def test_the_circuit_drawn_round_that_city_is_a_diverse_circuit_of_the_sites_it_joins() -> None:
    assert [
        (drawn_circuit.reason, drawn_circuit.requested_by)
        for drawn_circuit in _TWO_LOBES.circuits
        if segment_key("b", "w") in fiber_segments_along(drawn_circuit.pop_ids)
    ] == [(CIRCUIT_FOR_TARGET, ("b", "c"))]


_HUB_SITES = ("a", "b", "c", "d")
_HUB_FIBER = physical({
    ("a", "b"): 10.0, ("c", "d"): 10.0,
    ("a", "x"): 1.0, ("b", "x"): 1.0, ("c", "x"): 1.0, ("d", "x"): 1.0,
    ("b", "c"): 30.0, ("d", "a"): 30.0,
})
_HUB = _drawn(_HUB_SITES, _HUB_FIBER, _asking())


def _round_the_hub(mesh: BackboneMesh) -> list[SynthesisCircuit]:
    return [
        drawn_circuit
        for drawn_circuit in mesh.circuits
        if "x" not in drawn_circuit.pop_ids
        and segment_key(drawn_circuit.source, drawn_circuit.target) in {("a", "c"), ("b", "d")}
    ]


def test_the_hub_every_sites_shortest_circuits_cross_is_given_a_circuit_round_it() -> None:
    assert _cut(_HUB) == set()


def test_a_backbone_asked_for_one_circuit_is_given_the_circuit_round_the_hub_all_the_same() -> None:
    assert _cut(_drawn(_HUB_SITES, _HUB_FIBER, _asking(1))) == set()


def test_the_circuit_drawn_round_the_hub_says_the_split_is_what_put_it_there() -> None:
    assert [drawn_circuit.reason for drawn_circuit in _round_the_hub(_HUB)] == [
        CIRCUIT_FOR_RELIEF
    ]


def test_the_circuit_drawn_round_the_hub_is_in_no_sites_own_requirement() -> None:
    assert [drawn_circuit.requested_by for drawn_circuit in _round_the_hub(_HUB)] == [()]


def test_a_city_no_fiber_goes_round_still_leaves_every_wan_pop_its_circuits() -> None:
    assert {
        end
        for drawn_circuit in _BOWTIE.circuits
        for end in (drawn_circuit.source, drawn_circuit.target)
    } == set(_LOBE_SITES)


def test_a_tenant_that_asked_for_one_circuit_is_given_the_circuit_round_the_city_too() -> None:
    assert [
        drawn_circuit.pop_ids
        for drawn_circuit in _ONE_WAY_OUT_LOBES.circuits
        if segment_key("b", "w") in fiber_segments_along(drawn_circuit.pop_ids)
    ] == [("b", "w", "c")]


_OFFERED_MESH = _drawn(
    fixtures.OFFERED_WAYS_SITES, fixtures.OFFERED_WAYS_FIBER, _TWO_DIVERSE_CIRCUITS
)


def _run_over(mesh: BackboneMesh) -> set[tuple[str, str]]:
    return {
        key
        for drawn_circuit in mesh.circuits
        for key in fiber_segments_along(drawn_circuit.pop_ids)
    }


def test_a_site_is_drawn_over_the_fiber_selected_for_it() -> None:
    assert _run_over(_OFFERED_MESH) <= _selected(
        fixtures.OFFERED_WAYS_FIBER, fixtures.OFFERED_WAYS_SITES, _TWO_DIVERSE_CIRCUITS
    )


_PRUNED = _drawn(_SQUARE_SITES, _SQUARE_FIBER, WanPopConstraints(
    removed_pairs=frozenset({segment_key("w", "x")}), number_of_diverse_circuits=2,
))
_PINNED_CHORD = _drawn(_SQUARE_SITES, _SQUARE_FIBER, WanPopConstraints(
    number_of_diverse_circuits=2, forced_pairs=frozenset({segment_key("w", "y")}),
))
_PINNED_SEGMENT = _drawn(_SQUARE_SITES, _SQUARE_FIBER, WanPopConstraints(
    number_of_diverse_circuits=2, forced_pairs=frozenset({segment_key("w", "x")}),
))


def test_a_pruned_pair_is_never_joined_by_a_drawn_circuit() -> None:
    assert segment_key("w", "x") not in _pairs(_PRUNED)


def test_a_pruned_pair_leaves_the_rest_of_the_backbone_drawn() -> None:
    assert segment_key("y", "z") in _pairs(_PRUNED)


def test_a_pinned_pair_is_joined_however_the_fiber_was_selected() -> None:
    assert segment_key("w", "y") in _pairs(_PINNED_CHORD)


def test_a_pinned_circuit_says_the_operator_is_what_put_it_there() -> None:
    assert _joining(_PINNED_CHORD, "w", "y").reason == CIRCUIT_FOR_PIN


def test_a_pinned_circuit_is_never_taken_back_out_as_unneeded() -> None:
    assert len(_PINNED_CHORD.circuits) == 5


def test_a_pin_over_fiber_the_synthesis_would_have_selected_anyway_is_still_a_pin() -> None:
    assert _joining(_PINNED_SEGMENT, "w", "x").reason == CIRCUIT_FOR_PIN


_ISLANDS = physical({("a", "b"): 1.0, ("c", "d"): 1.0})
_ISLAND_PIN = _drawn(("a", "c"), _ISLANDS, WanPopConstraints(
    forced_pairs=frozenset({segment_key("a", "c")}),
))


def test_a_backbone_the_fiber_never_joins_is_drawn_with_no_circuits() -> None:
    assert not _ISLAND_PIN.circuits


def test_a_backbone_the_fiber_never_joins_is_floored_at_nothing() -> None:
    assert _ISLAND_PIN.lower_bound_miles == 0.0


def test_a_site_the_fiber_does_not_carry_leaves_the_others_their_circuits() -> None:
    fiber = physical({("a", "b"): 1.0})
    mesh = _drawn(("a", "b", "zed"), fiber, WanPopConstraints(number_of_diverse_circuits=1))
    assert _pairs(mesh) == {segment_key("a", "b")}


def test_miles_along_adds_up_the_segments_a_circuit_crosses() -> None:
    assert miles_along(("w", "x", "y"), _SQUARE_FIBER) == 200.0


def _use(source: str, target: str, pop_ids: tuple[str, ...], miles: float) -> SynthesisCircuit:
    return SynthesisCircuit("backbone_mesh", source, target, pop_ids, miles)


_RING_PLUS_CHORD = [
    _use("w", "x", ("w", "x"), 100.0),
    _use("x", "y", ("x", "y"), 100.0),
    _use("y", "z", ("y", "z"), 100.0),
    _use("z", "w", ("z", "w"), 100.0),
    _use("w", "y", ("w", "y"), 250.0),
]
_TRIANGLE = [
    _use("a", "b", ("a", "b"), 1.0),
    _use("b", "c", ("b", "c"), 1.0),
    _use("a", "c", ("a", "c"), 1.0),
]
_CHAIN = [
    _use("a", "b", ("a", "b"), 1.0),
    _use("b", "c", ("b", "c"), 1.0),
    _use("c", "d", ("c", "d"), 1.0),
]


def test_a_circuit_nobody_needs_is_taken_back_out() -> None:
    assert _needed(_RING_PLUS_CHORD, _SQUARE_SITES, 2) == _RING_PLUS_CHORD[:4]


def test_a_circuit_a_site_would_lose_a_diverse_circuit_by_is_kept() -> None:
    assert _needed(_RING_PLUS_CHORD[:4], _SQUARE_SITES, 2) == _RING_PLUS_CHORD[:4]


def test_a_circuit_whose_loss_would_leave_a_city_carrying_the_network_is_kept() -> None:
    assert _needed(_TRIANGLE, ("a", "b", "c"), 1) == _TRIANGLE


def test_a_circuit_whose_loss_would_break_the_backbone_in_two_is_kept() -> None:
    assert _needed(_CHAIN, ("a", "b", "c", "d"), 1) == _CHAIN


def test_a_synthesis_that_never_survived_a_city_loss_is_not_held_to_surviving_one() -> None:
    doubled = [*_CHAIN, _use("a", "b", ("a", "b"), 9.0)]
    assert _needed(doubled, ("a", "b", "c", "d"), 1) == _CHAIN


_SQUARE_CHANGING_HANDS = fixtures.carrier_fiber_segments({
    ("w", "x"): (100.0, ("lumen",)),
    ("x", "y"): (100.0, ("zayo",)),
    ("w", "z"): (150.0, ("lumen",)),
    ("z", "y"): (150.0, ("zayo",)),
})
_PIN_WY = WanPopConstraints(
    number_of_diverse_circuits=2, forced_pairs=frozenset({segment_key("w", "y")}),
)


def test_a_pin_is_drawn_over_the_shortest_way_though_that_way_changes_hands() -> None:
    mesh = _drawn(("w", "x", "y", "z"), _SQUARE_CHANGING_HANDS, _PIN_WY)
    assert [
        drawn_circuit.pop_ids
        for drawn_circuit in mesh.circuits
        if drawn_circuit.reason == CIRCUIT_FOR_PIN
    ] == [
        ("w", "x", "y"),
    ]


_STUB_SITES = ("a", "f", "g", "m", "s")
_STUB_AND_CHORD = [
    _use("a", "g", ("a", "p", "g"), 200.0),
    _use("a", "g", ("a", "q", "g"), 150.0),
    _use("a", "s", ("a", "s"), 300.0),
    _use("f", "g", ("f", "g"), 60.0),
    _use("g", "s", ("g", "s"), 40.0),
    _use("f", "s", ("f", "s"), 140.0),
    _use("g", "m", ("g", "m"), 60.0),
    _use("f", "s", ("f", "r", "s"), 500.0),
]


def test_a_circuit_that_stops_a_pop_cutting_the_wan_further_is_kept() -> None:
    assert _STUB_AND_CHORD[2] in _needed(_STUB_AND_CHORD, _STUB_SITES, 2)


def test_a_spare_circuit_beside_an_irreparable_cut_is_still_taken_back_out() -> None:
    assert _STUB_AND_CHORD[7] not in _needed(_STUB_AND_CHORD, _STUB_SITES, 2)
