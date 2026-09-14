from __future__ import annotations

import pytest

import fixtures
from synthesizer.ceiling import CircuitProofInputs, diverse_circuit_ceilings
from synthesizer.graphs import build_adjacency
from synthesizer.input_graph import FiberSegment
from synthesizer.survivable import (
    FiberInputs,
    FiberSelection,
    _Requirement,
    _answered_by_every_wan,
    _carried,
    _held,
    _shortfalls,
    _diverse_circuits_out_of,
    _two_circuits_sharing_no_pop,
    _writing,
    select_fiber,
)

physical = fixtures.fiber_segments_from

_DIVERSE_CIRCUITS = 2
_SLACK = 1e-6


def _asking(
    fiber: dict[tuple[str, str], FiberSegment],
    wan_pop_ids: tuple[str, ...],
    number_of_diverse_circuits: int = _DIVERSE_CIRCUITS,
) -> FiberInputs:
    return FiberInputs(wan_pop_ids, fiber, number_of_diverse_circuits)


def _selected(
    fiber: dict[tuple[str, str], FiberSegment],
    wan_pop_ids: tuple[str, ...],
    number_of_diverse_circuits: int = _DIVERSE_CIRCUITS,
) -> FiberSelection:
    return select_fiber(_asking(fiber, wan_pop_ids, number_of_diverse_circuits))


def _owed(
    fiber: dict[tuple[str, str], FiberSegment],
    wan_pop_ids: tuple[str, ...],
    site: str,
    number_of_diverse_circuits: int = _DIVERSE_CIRCUITS,
) -> int:
    inputs = _asking(fiber, wan_pop_ids, number_of_diverse_circuits)
    return sum(
        row.required
        for row in _diverse_circuits_out_of(site, _writing(inputs, _whole(inputs)))
    )


def _whole(inputs: FiberInputs) -> dict[tuple[str, str], float]:
    return {
        key: segment.distance_miles for key, segment in inputs.fiber_segments.items()
    }


def _selected_miles(
    selection: FiberSelection, fiber: dict[tuple[str, str], FiberSegment]
) -> float:
    return sum(fiber[key].distance_miles for key in selection.segments)


_CROSSING_SITES = ("eug", "hil", "sea")
_OVERLAND = frozenset({("eug", "pdx"), ("hil", "pdx"), ("pdx", "sea")})
_UNDER_WATER_SELECTION = _selected(fixtures.CROSSING_SUBMARINE_FIBER, _CROSSING_SITES)


def test_no_submarine_fiber_is_selected_where_a_circuit_over_land_exists() -> None:
    assert _UNDER_WATER_SELECTION.segments == _OVERLAND


_NO_FIBER = _selected(physical({}), ("a", "b"))
_NO_SITES = _selected(physical({("a", "b"): 1.0}), ())


def test_a_backbone_with_no_fiber_at_all_holds_nothing_and_is_floored_at_nothing() -> None:
    assert _NO_FIBER == FiberSelection(frozenset(), 0.0)


def test_a_backbone_with_no_sites_selects_none_of_the_fiber_in_front_of_it() -> None:
    assert not _NO_SITES.segments


def test_a_backbone_with_no_sites_is_floored_at_nothing_rather_than_at_what_is_on_offer() -> None:
    assert _NO_SITES.lower_bound_miles == pytest.approx(0.0)


_RING_PAIRS = {("a", "b"): 1.0, ("b", "c"): 1.0, ("c", "d"): 1.0, ("a", "d"): 1.0}
_RING_SITES = ("a", "b", "c", "d")
_RING_SEGMENTS = frozenset(_RING_PAIRS)
_RING = physical(_RING_PAIRS)
_CHORD = physical({**_RING_PAIRS, ("a", "c"): 10.0})
_RING_SELECTION = _selected(_RING, _RING_SITES)
_CHORD_SELECTION = _selected(_CHORD, _RING_SITES)


def test_a_ring_is_selected_whole_because_nothing_short_of_it_gives_two_diverse_circuits() -> None:
    assert _RING_SELECTION.segments == _RING_SEGMENTS


def test_the_floor_under_the_ring_is_the_mileage_of_the_ring_itself() -> None:
    assert _RING_SELECTION.lower_bound_miles == pytest.approx(4.0)


def test_fiber_no_requirement_turns_on_is_left_where_it_is() -> None:
    assert _CHORD_SELECTION.segments == _RING_SEGMENTS


_CHAIN = physical({("a", "b"): 1.0, ("b", "c"): 1.0})
_CHAIN_SELECTION = _selected(_CHAIN, ("a", "b", "c"))


def test_a_site_behind_a_single_point_of_failure_is_asked_for_what_its_fiber_can_carry() -> None:
    assert _CHAIN_SELECTION.segments == frozenset(_CHAIN)


_ONLY_REACHABLE_PEER = physical({
    ("a", "b"): 20.0, ("b", "e"): 22.0,
    ("a", "f"): 32.0, ("b", "f"): 32.0,
    ("b", "g"): 32.0, ("e", "g"): 32.0,
})
_ONLY_REACHABLE_PEER_SELECTION = _selected(_ONLY_REACHABLE_PEER, ("a", "b", "e"))


def test_the_fiber_selected_carries_both_circuits_to_a_wan_pops_only_reachable_peer() -> None:
    assert _ONLY_REACHABLE_PEER_SELECTION.segments == frozenset(_ONLY_REACHABLE_PEER)


def test_the_floor_states_both_circuits_to_a_wan_pops_only_reachable_peer() -> None:
    assert _ONLY_REACHABLE_PEER_SELECTION.lower_bound_miles == pytest.approx(170.0)


_ASKED_TWO_OVER_ONE = _Requirement(
    "a", frozenset({"b"}), frozenset({"a"}), _DIVERSE_CIRCUITS, frozenset()
)


def test_a_requirement_is_lowered_to_the_circuits_the_whole_fiber_can_carry() -> None:
    assert _carried(_ASKED_TWO_OVER_ONE, {("a", "b"): 1.0}) == 1


_UNDER_WATER_PAIRS = {
    ("a", "p"): 10.0, ("b", "p"): 10.0, ("a", "q"): 20.0, ("b", "q"): 20.0,
}
_UNDER_WATER_ONLY = fixtures.fiber_segments_under_water(
    _UNDER_WATER_PAIRS, set(_UNDER_WATER_PAIRS)
)
_UNDER_WATER_ONLY_SELECTION = _selected(_UNDER_WATER_ONLY, ("a", "b"))


def test_submarine_fiber_is_selected_where_a_peer_is_reachable_no_other_way() -> None:
    assert _UNDER_WATER_ONLY_SELECTION.segments == frozenset(_UNDER_WATER_ONLY)


_TWO_SHORES = fixtures.fiber_segments_under_water(
    {
        ("a", "b"): 10.0, ("a", "x"): 50.0, ("x", "b"): 50.0,
        ("a", "c"): 1000.0, ("b", "c"): 1000.0,
    },
    {("a", "c"), ("b", "c")},
)
_TWO_SHORE_SITES = ("a", "b", "c")
_TWO_SHORE_INPUTS = _asking(_TWO_SHORES, _TWO_SHORE_SITES)
_TWO_SHORE_WRITING = _writing(_TWO_SHORE_INPUTS, _whole(_TWO_SHORE_INPUTS))
_TWO_SHORE_SELECTION = _selected(_TWO_SHORES, _TWO_SHORE_SITES)
_THE_SECOND_WAY_OVER_LAND = frozenset({("a", "x"), ("b", "x")})
_ARRIVING_ON_THE_NEAR_SHORE = frozenset({("c", "a"), ("c", "b")})
_ONE_SHORE = fixtures.fiber_segments_under_water(
    {**_RING_PAIRS, ("a", "c"): 10.0}, {("a", "c")}
)
_ONE_SHORE_INPUTS = _asking(_ONE_SHORE, _RING_SITES)
_ONE_SHORE_WRITING = _writing(_ONE_SHORE_INPUTS, _whole(_ONE_SHORE_INPUTS))
_ARRIVING_ON_THE_ONLY_SHORE = frozenset({("a", "c"), ("c", "a")})


def test_a_pops_own_circuits_admit_no_crossing_arriving_on_its_shore() -> None:
    assert _diverse_circuits_out_of("a", _TWO_SHORE_WRITING)[0].barred == (
        _ARRIVING_ON_THE_NEAR_SHORE
    )


def test_a_pair_on_a_wan_spanning_two_shores_is_joined_over_any_fiber() -> None:
    assert _two_circuits_sharing_no_pop(_TWO_SHORE_WRITING)[0].barred == frozenset()


def test_a_pair_on_a_wan_held_to_one_shore_is_joined_over_land_alone() -> None:
    assert _two_circuits_sharing_no_pop(_ONE_SHORE_WRITING)[0].barred == (
        _ARRIVING_ON_THE_ONLY_SHORE
    )


def test_a_pair_on_one_shore_is_joined_the_long_way_round_through_a_pop_across_the_water(
) -> None:
    assert not _TWO_SHORE_SELECTION.segments & _THE_SECOND_WAY_OVER_LAND


def test_the_floor_states_a_circuit_over_land_and_a_crossing_for_a_pop_with_a_peer_on_each_shore(
) -> None:
    assert _TWO_SHORE_SELECTION.lower_bound_miles == pytest.approx(2010.0)


_TWIN_CIRCUITS = physical({
    ("a", "p"): 1.0, ("b", "p"): 1.0, ("a", "q"): 1.0, ("b", "q"): 1.0,
})
_TWIN_SELECTION = _selected(_TWIN_CIRCUITS, ("a", "b"))


def test_a_pair_allowed_two_circuits_between_them_is_given_both() -> None:
    assert _TWIN_SELECTION.segments == frozenset(_TWIN_CIRCUITS)


_TWIN_SPLIT = fixtures.carrier_fiber_segments({
    ("a", "p"): (1.0, ("zayo",)),
    ("b", "p"): (1.0, ("zayo",)),
    ("a", "q"): (1.0, ("zayo",)),
    ("b", "q"): (1.0, ("lumen",)),
})
_TWIN_OWNED = fixtures.carrier_fiber_segments({
    ("a", "p"): (1.0, ("zayo",)),
    ("b", "p"): (1.0, ("zayo",)),
    ("a", "q"): (1.0, ("lumen",)),
    ("b", "q"): (1.0, ("lumen",)),
})
_TWIN_SPLIT_SELECTION = _selected(_TWIN_SPLIT, ("a", "b"))
_CHAIN_ASKED_ONE = _selected(_CHAIN, ("a", "b", "c"), number_of_diverse_circuits=1)


def test_a_site_is_owed_a_diverse_circuit_that_changes_hands() -> None:
    assert _owed(_TWIN_SPLIT, ("a", "b"), "a") == 2


def test_a_site_is_owed_both_diverse_circuits_where_one_carrier_has_each() -> None:
    assert _owed(_TWIN_OWNED, ("a", "b"), "a") == 2


def test_fiber_nobody_owns_is_owed_like_anybodys() -> None:
    assert _owed(_TWIN_CIRCUITS, ("a", "b"), "a") == 2


def test_a_wan_pop_asked_for_one_circuit_is_owed_the_two_the_directive_requires() -> None:
    assert _owed(_TWIN_CIRCUITS, ("a", "b"), "a", number_of_diverse_circuits=1) == 2


def test_the_fiber_selected_carries_the_circuit_that_changes_hands() -> None:
    assert _TWIN_SPLIT_SELECTION.segments == frozenset(_TWIN_SPLIT)


def test_the_floor_is_measured_over_the_requirements_the_build_is_held_to() -> None:
    assert _CHAIN_SELECTION.lower_bound_miles == pytest.approx(
        _CHAIN_ASKED_ONE.lower_bound_miles
    )


_SHARED_TRANSIT_SELECTION = _selected(
    fixtures.SHARED_TRANSIT_FIBER, fixtures.SHARED_TRANSIT_SITES
)


def _shared_transit_ceilings(segments: frozenset[tuple[str, str]]) -> dict[str, int]:
    held = {segment: fixtures.SHARED_TRANSIT_FIBER[segment] for segment in segments}
    return diverse_circuit_ceilings(CircuitProofInputs(
        fixtures.SHARED_TRANSIT_SITES, build_adjacency(held)
    ))


def test_the_fiber_selected_where_two_carriers_share_a_pop_carries_both_diverse_circuits() -> None:
    assert _shared_transit_ceilings(_SHARED_TRANSIT_SELECTION.segments) == {"a": 2, "b": 2}


def test_the_floor_is_stated_over_the_circuit_round_the_pop_two_carriers_share() -> None:
    assert _SHARED_TRANSIT_SELECTION.lower_bound_miles >= (
        fixtures.SHARED_TRANSIT_MILES - _SLACK
    )


_TWO_TRIANGLES = physical({
    ("a", "b"): 1.0, ("b", "c"): 1.0, ("a", "c"): 1.0,
    ("d", "e"): 1.0, ("e", "f"): 1.0, ("d", "f"): 1.0,
    ("c", "d"): 1.0,
})
_TRIANGLE_SITES = ("a", "b", "c", "d", "e", "f")
_TRIANGLES_SELECTION = _selected(_TWO_TRIANGLES, _TRIANGLE_SITES)


def test_no_fiber_is_selected_for_a_pair_the_whole_fiber_cannot_join_twice() -> None:
    assert ("c", "d") not in _TRIANGLES_SELECTION.segments


_HANDED_OFF = frozenset({("a", "p"), ("b", "p"), ("a", "q"), ("b", "q")})


def test_the_fiber_selected_is_the_shortest_though_every_circuit_over_it_changes_hands() -> None:
    assert _selected(
        fixtures.OFFERED_WAYS_FIBER, fixtures.OFFERED_WAYS_SITES
    ).segments == _HANDED_OFF


_DISTANT_PEER_SITES = ("hil", "sea", "syd")
_DISTANT_PEER_SELECTION = _selected(fixtures.DISTANT_PEER_FIBER, _DISTANT_PEER_SITES)


def _distant_peer_ceilings(segments: frozenset[tuple[str, str]]) -> dict[str, int]:
    return diverse_circuit_ceilings(CircuitProofInputs(
        _DISTANT_PEER_SITES,
        build_adjacency({
            segment: fixtures.DISTANT_PEER_FIBER[segment] for segment in segments
        }),
    ))


def test_the_fiber_selected_for_a_site_carries_the_diverse_circuits_it_asked_for() -> None:
    assert _distant_peer_ceilings(_DISTANT_PEER_SELECTION.segments) == {
        "hil": 2, "sea": 2, "syd": 2,
    }


_MANY_PASS = physical(fixtures.MANY_PASS_SEGMENTS)
_MANY_PASS_INPUTS = _asking(_MANY_PASS, fixtures.MANY_PASS_SITES)
_MANY_PASS_SELECTION = _selected(_MANY_PASS, fixtures.MANY_PASS_SITES)
_MANY_PASS_FIBER = _whole(_MANY_PASS_INPUTS)


def test_a_search_that_runs_long_enough_selects_the_shortest_synthesis_there_is() -> None:
    assert _selected_miles(_MANY_PASS_SELECTION, _MANY_PASS) == pytest.approx(
        _MANY_PASS_SELECTION.lower_bound_miles
    )


def test_the_fiber_a_long_search_settles_on_meets_every_requirement_asked_of_it() -> None:
    assert not _shortfalls(
        _answered_by_every_wan(_writing(_MANY_PASS_INPUTS, _MANY_PASS_FIBER)),
        _held(_MANY_PASS_FIBER, _MANY_PASS_SELECTION.segments),
    )


_NEARER_PEER_SELECTION = _selected(
    fixtures.NEARER_PEER_FIBER,
    fixtures.NEARER_PEER_SITES,
    number_of_diverse_circuits=fixtures.NEARER_PEER_CIRCUITS,
)


def test_the_floor_is_stated_over_no_row_handing_a_wan_pops_ask_to_its_nearer_peers() -> None:
    assert _NEARER_PEER_SELECTION.lower_bound_miles == pytest.approx(fixtures.NEARER_PEER_MILES)


def test_the_fiber_selected_for_a_wan_pop_asked_for_three_circuits_runs_the_fewest_miles() -> None:
    assert _selected_miles(_NEARER_PEER_SELECTION, fixtures.NEARER_PEER_FIBER) == pytest.approx(
        fixtures.NEARER_PEER_MILES
    )


_CASES: tuple[tuple[str, FiberSelection, dict[tuple[str, str], FiberSegment]], ...] = (
    ("ring", _RING_SELECTION, _RING),
    ("ring and chord", _CHORD_SELECTION, _CHORD),
    ("chain", _CHAIN_SELECTION, _CHAIN),
    ("two triangles", _TRIANGLES_SELECTION, _TWO_TRIANGLES),
    ("pair with two circuits", _TWIN_SELECTION, _TWIN_CIRCUITS),
    ("pair whose second circuit changes hands", _TWIN_SPLIT_SELECTION, _TWIN_SPLIT),
    ("twelve cities and five wan pops", _MANY_PASS_SELECTION, _MANY_PASS),
    ("six wan pops asked for three circuits", _NEARER_PEER_SELECTION, fixtures.NEARER_PEER_FIBER),
)


def test_no_selection_is_floored_above_the_fiber_it_actually_holds() -> None:
    assert [
        name
        for name, selection, fiber in _CASES
        if selection.lower_bound_miles > _selected_miles(selection, fiber) + _SLACK
    ] == []


def test_every_selection_runs_the_miles_of_the_floor_stated_under_it() -> None:
    assert [
        name
        for name, selection, fiber in _CASES
        if abs(selection.lower_bound_miles - _selected_miles(selection, fiber)) > _SLACK
    ] == []


_SHORT_AND_LONG_SELECTION = _selected(
    fixtures.SHORT_AND_LONG_FIBER, fixtures.SHORT_AND_LONG_SITES
)
_ONLY_LONG_SELECTION = _selected(fixtures.ONLY_LONG_FIBER, fixtures.SHORT_AND_LONG_SITES)


def test_the_shorter_of_two_circuits_is_the_one_selected() -> None:
    assert not _SHORT_AND_LONG_SELECTION.segments & fixtures.THE_LONG_CIRCUIT


def test_the_only_circuit_there_is_gets_selected_however_far_it_runs() -> None:
    assert fixtures.THE_LONG_CIRCUIT <= _ONLY_LONG_SELECTION.segments


_ALREADY_NEEDED_SELECTION = _selected(
    fixtures.ALREADY_NEEDED_FIBER, fixtures.ALREADY_NEEDED_SITES
)


def test_the_floor_is_stated_over_every_diverse_circuit_a_wan_pop_is_owed() -> None:
    assert _ALREADY_NEEDED_SELECTION.lower_bound_miles == pytest.approx(
        fixtures.ALREADY_NEEDED_MILES
    )


def test_the_fiber_selected_carries_the_segment_only_a_wan_pops_second_circuit_needs() -> None:
    assert fixtures.THE_SEGMENT_ONLY_A_SECOND_CIRCUIT_NEEDS <= _ALREADY_NEEDED_SELECTION.segments


_ON_ONE_POP = {
    ("a", "b"): 10.0, ("a", "p"): 10.0, ("b", "p"): 10.0,
    ("c", "d"): 10.0, ("c", "p"): 10.0, ("d", "p"): 10.0,
}
_PAST_THE_POP = {**_ON_ONE_POP, ("a", "c"): 200.0}
_ON_ONE_POP_SITES = ("a", "b", "c", "d")
_HELD_AT_ONE_POP = _selected(physical(_ON_ONE_POP), _ON_ONE_POP_SITES)
_PAST_THE_POP_SELECTION = _selected(physical(_PAST_THE_POP), _ON_ONE_POP_SITES)
_PAST_THE_POP_ASKED_ONE = _selected(
    physical(_PAST_THE_POP), _ON_ONE_POP_SITES, number_of_diverse_circuits=1
)


def test_the_floor_is_stated_over_the_circuits_that_keep_one_pop_from_splitting_the_wan() -> None:
    assert _PAST_THE_POP_SELECTION.lower_bound_miles == pytest.approx(240.0)


def test_no_such_circuit_is_stated_over_fiber_that_offers_no_way_past_the_pop() -> None:
    assert _HELD_AT_ONE_POP.lower_bound_miles == pytest.approx(60.0)


def test_a_backbone_asked_for_one_circuit_is_stated_the_circuits_that_keep_it_whole() -> None:
    assert _PAST_THE_POP_ASKED_ONE.lower_bound_miles == pytest.approx(240.0)


def test_the_fiber_selected_holds_the_circuit_that_keeps_one_pop_from_splitting_the_wan() -> None:
    assert ("a", "c") in _PAST_THE_POP_SELECTION.segments


def test_the_fiber_selected_runs_the_miles_the_floor_states_for_surviving_the_pop() -> None:
    assert _selected_miles(_PAST_THE_POP_SELECTION, physical(_PAST_THE_POP)) == pytest.approx(
        240.0
    )


def test_a_backbone_asked_for_one_circuit_is_selected_the_way_past_every_pop() -> None:
    assert _selected_miles(_PAST_THE_POP_ASKED_ONE, physical(_PAST_THE_POP)) == pytest.approx(
        240.0
    )


_ONE_CIRCUIT_SEAT = {**_PAST_THE_POP, ("d", "m"): 5.0}
_ONE_CIRCUIT_SEAT_SELECTION = _selected(
    physical(_ONE_CIRCUIT_SEAT), (*_ON_ONE_POP_SITES, "m")
)


def test_a_wan_pop_the_fiber_can_give_one_circuit_is_stated_no_way_past_any_pop() -> None:
    assert _ONE_CIRCUIT_SEAT_SELECTION.lower_bound_miles == pytest.approx(55.0)


_TWO_WAYS_TO_ONE_PEER = physical(fixtures.TWO_WAYS_TO_ONE_PEER_SEGMENTS)
_TWO_WAYS_SELECTION = _selected(_TWO_WAYS_TO_ONE_PEER, fixtures.TWO_WAYS_TO_ONE_PEER_WAN_POPS)


def test_the_fiber_selected_carries_as_many_ways_out_as_the_grader_credits() -> None:
    assert diverse_circuit_ceilings(CircuitProofInputs(
        fixtures.TWO_WAYS_TO_ONE_PEER_WAN_POPS,
        build_adjacency({
            segment: _TWO_WAYS_TO_ONE_PEER[segment] for segment in _TWO_WAYS_SELECTION.segments
        }),
    ))["a"] == fixtures.two_ways_to_one_peer_credited() == 2
