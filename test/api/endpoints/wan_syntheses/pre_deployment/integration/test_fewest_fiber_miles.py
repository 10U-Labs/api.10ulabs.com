from __future__ import annotations

import pytest

import fixtures
from synthesizer import linear_program
from synthesizer.model import SynthesisArtifacts
from synthesizer.survivable import FiberInputs, select_fiber

_SITES = ("w", "x", "y", "z")
_ASKED_FOR = 2
_SEGMENTS = {
    ("w", "x"): 100.0, ("x", "y"): 100.0, ("y", "z"): 100.0, ("z", "w"): 100.0,
    ("w", "y"): 250.0, ("x", "z"): 250.0,
}
ARTIFACTS = fixtures.synthesis_over_segments(_SITES, _SEGMENTS, _ASKED_FOR)
_MESH = fixtures.mesh_circuits(ARTIFACTS)


def test_the_delivered_synthesis_runs_over_the_four_hundred_miles_of_the_ring() -> None:
    assert ARTIFACTS.synthesis.metrics.physical_miles == 400.0


def test_the_delivered_synthesis_draws_one_circuit_a_pair_round_the_ring() -> None:
    assert sum(drawn_circuit.distance_miles for drawn_circuit in _MESH) == 400.0


def test_the_delivered_synthesis_publishes_the_floor_it_is_judged_against() -> None:
    assert round(ARTIFACTS.synthesis.metrics.backbone_lower_bound_miles, 3) == 400.0


def test_the_delivered_synthesis_runs_no_further_than_twice_that_floor() -> None:
    assert (
        ARTIFACTS.synthesis.metrics.physical_miles
        <= 2 * ARTIFACTS.synthesis.metrics.backbone_lower_bound_miles
    )


def test_every_site_still_holds_the_two_diverse_circuits_it_was_owed() -> None:
    assert ARTIFACTS.validation["backbone_mesh_independence_deficient"] == []


def _many_pass_artifacts() -> SynthesisArtifacts:
    return fixtures.synthesis_over_segments(
        fixtures.MANY_PASS_SITES,
        fixtures.MANY_PASS_SEGMENTS,
        _ASKED_FOR,
        transit_ids=fixtures.MANY_PASS_TRANSIT,
    )


MANY_PASS_ARTIFACTS = _many_pass_artifacts()


def test_a_synthesis_whose_search_takes_many_passes_runs_the_fewest_miles_there_are() -> None:
    assert MANY_PASS_ARTIFACTS.synthesis.metrics.physical_miles == fixtures.MANY_PASS_MILES


def test_that_synthesis_runs_exactly_the_floor_it_publishes_rather_than_twice_it() -> None:
    assert MANY_PASS_ARTIFACTS.synthesis.metrics.physical_miles == pytest.approx(
        MANY_PASS_ARTIFACTS.synthesis.metrics.backbone_lower_bound_miles
    )


def test_every_wan_pop_on_that_synthesis_holds_the_two_diverse_circuits_it_was_owed() -> None:
    assert MANY_PASS_ARTIFACTS.validation["backbone_mesh_independence_deficient"] == []


def test_that_synthesis_is_the_same_synthesis_when_every_pass_of_its_search_gives_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(linear_program, "_SECONDS_A_PASS_MAY_RUN", 0.0)
    assert _many_pass_artifacts().synthesis.metrics.physical_miles == fixtures.MANY_PASS_MILES


_SPLIT_SITES = ("w", "x")
_SPLIT_TRANSIT = ("p", "q")
_SPLIT_SEGMENTS: dict[tuple[str, str], tuple[float, tuple[str, ...]]] = {
    ("w", "p"): (100.0, ("lumen",)),
    ("p", "x"): (100.0, ("lumen",)),
    ("w", "q"): (150.0, ("zayo",)),
    ("q", "x"): (150.0, ("lumen",)),
}
SPLIT_ARTIFACTS = fixtures.synthesis_over_owned_fiber(
    _SPLIT_SITES, _SPLIT_SEGMENTS, _ASKED_FOR, _SPLIT_TRANSIT
)
_SLACK = 1e-6


def test_no_synthesis_runs_fewer_miles_than_the_floor_it_publishes() -> None:
    assert SPLIT_ARTIFACTS.synthesis.metrics.physical_miles >= (
        SPLIT_ARTIFACTS.synthesis.metrics.backbone_lower_bound_miles - _SLACK
    )


def test_a_site_whose_second_circuit_changes_hands_is_drawn_that_circuit() -> None:
    assert ("w", "q", "x") in {
        drawn_circuit.pop_ids for drawn_circuit in fixtures.mesh_circuits(SPLIT_ARTIFACTS)
    }


def test_a_site_whose_second_circuit_changes_hands_is_floored_at_both_circuits() -> None:
    assert SPLIT_ARTIFACTS.synthesis.metrics.backbone_lower_bound_miles == pytest.approx(500.0)


OFFERED_ARTIFACTS = fixtures.synthesis_over_owned_fiber(
    fixtures.OFFERED_WAYS_SITES,
    fixtures.OFFERED_WAYS_SEGMENTS,
    _ASKED_FOR,
    fixtures.OFFERED_WAYS_TRANSIT,
)


def _fiber_the_selection_holds() -> frozenset[tuple[str, str]]:
    return select_fiber(FiberInputs(
        fixtures.OFFERED_WAYS_SITES, fixtures.OFFERED_WAYS_FIBER, _ASKED_FOR
    )).segments


def test_the_delivered_synthesis_holds_only_fiber_selected_for_it() -> None:
    assert set(OFFERED_ARTIFACTS.synthesis.fiber_segment_keys) <= _fiber_the_selection_holds()


SHARED_TRANSIT_ARTIFACTS = fixtures.synthesis_over_owned_fiber(
    fixtures.SHARED_TRANSIT_SITES,
    fixtures.SHARED_TRANSIT_SEGMENTS,
    _ASKED_FOR,
    fixtures.SHARED_TRANSIT_TRANSIT,
)


def _fiber_selected_where_two_carriers_share_a_pop() -> frozenset[tuple[str, str]]:
    return select_fiber(FiberInputs(
        fixtures.SHARED_TRANSIT_SITES, fixtures.SHARED_TRANSIT_FIBER, _ASKED_FOR
    )).segments


def test_the_synthesis_over_a_shared_pop_is_drawn_over_the_fiber_selected_for_it() -> None:
    assert set(SHARED_TRANSIT_ARTIFACTS.synthesis.fiber_segment_keys) <= (
        _fiber_selected_where_two_carriers_share_a_pop()
    )


def test_that_synthesis_runs_no_further_than_a_tenth_past_the_floor_it_publishes() -> None:
    assert SHARED_TRANSIT_ARTIFACTS.synthesis.metrics.physical_miles <= (
        1.1 * SHARED_TRANSIT_ARTIFACTS.synthesis.metrics.backbone_lower_bound_miles
    )


SHORT_AND_LONG_ARTIFACTS = fixtures.synthesis_over_segments(
    fixtures.SHORT_AND_LONG_SITES,
    fixtures.SHORT_AND_LONG_SEGMENTS,
    _ASKED_FOR,
    fixtures.SHORT_AND_LONG_TRANSIT,
)


def test_the_delivered_synthesis_holds_the_shorter_of_two_circuits() -> None:
    assert not set(
        SHORT_AND_LONG_ARTIFACTS.synthesis.fiber_segment_keys
    ) & fixtures.THE_LONG_CIRCUIT


_PAIRED_SITES = ("a", "b", "c", "d")
_PAIRED_TRANSIT = ("t0", "t1", "t2")
_PAIRED_SEGMENTS = {
    ("a", "c"): 100.0, ("a", "t1"): 80.0,
    ("b", "d"): 40.0, ("b", "t2"): 50.0,
    ("c", "t2"): 110.0,
    ("d", "t0"): 90.0, ("d", "t2"): 30.0,
    ("t0", "t1"): 100.0, ("t1", "t2"): 110.0,
}
PAIRED_ARTIFACTS = fixtures.synthesis_over_segments(
    _PAIRED_SITES, _PAIRED_SEGMENTS, _ASKED_FOR, _PAIRED_TRANSIT
)


def test_the_floor_is_stated_over_the_diverse_circuits_owed_and_the_loss_of_any_one_pop() -> None:
    assert round(PAIRED_ARTIFACTS.synthesis.metrics.backbone_lower_bound_miles, 3) == 570.0


def test_that_synthesis_runs_no_fewer_miles_than_the_floor_it_publishes() -> None:
    assert PAIRED_ARTIFACTS.synthesis.metrics.physical_miles >= (
        PAIRED_ARTIFACTS.synthesis.metrics.backbone_lower_bound_miles - _SLACK
    )


def test_no_pop_that_synthesis_runs_through_splits_it_by_being_lost() -> None:
    assert PAIRED_ARTIFACTS.validation["biconnected_no_articulation_points"]


FLOORED_ABOVE_ARTIFACTS = fixtures.synthesis_over_owned_fiber(
    fixtures.FLOORED_ABOVE_SITES,
    fixtures.FLOORED_ABOVE_SEGMENTS,
    _ASKED_FOR,
    fixtures.FLOORED_ABOVE_TRANSIT,
)


def test_the_floor_published_is_no_higher_than_the_miles_the_synthesis_runs_over() -> None:
    assert FLOORED_ABOVE_ARTIFACTS.synthesis.metrics.backbone_lower_bound_miles <= (
        FLOORED_ABOVE_ARTIFACTS.synthesis.metrics.physical_miles + _SLACK
    )


def test_that_floor_is_the_fewest_miles_the_diverse_circuits_it_grades_can_run_over() -> None:
    assert round(
        FLOORED_ABOVE_ARTIFACTS.synthesis.metrics.backbone_lower_bound_miles, 3
    ) == fixtures.FLOORED_ABOVE_MILES


def test_every_wan_pop_on_that_synthesis_still_holds_the_diverse_circuits_it_was_owed() -> None:
    assert FLOORED_ABOVE_ARTIFACTS.validation["backbone_mesh_independence_deficient"] == []


NEARER_PEER_ARTIFACTS = fixtures.synthesis_over_segments(
    fixtures.NEARER_PEER_SITES, fixtures.NEARER_PEER_SEGMENTS, fixtures.NEARER_PEER_CIRCUITS
)


def test_a_synthesis_asked_for_three_circuits_runs_no_fewer_miles_than_its_floor() -> None:
    assert NEARER_PEER_ARTIFACTS.synthesis.metrics.physical_miles >= (
        NEARER_PEER_ARTIFACTS.synthesis.metrics.backbone_lower_bound_miles - _SLACK
    )


def test_that_floor_is_the_fewest_miles_three_circuits_out_of_every_wan_pop_can_run_over() -> None:
    assert round(
        NEARER_PEER_ARTIFACTS.synthesis.metrics.backbone_lower_bound_miles, 3
    ) == fixtures.NEARER_PEER_MILES


def test_every_wan_pop_on_that_synthesis_holds_the_three_diverse_circuits_it_was_owed() -> None:
    assert NEARER_PEER_ARTIFACTS.validation["backbone_mesh_independence_deficient"] == []


_ON_ONE_POP_SITES = ("a", "b", "c", "d")
_ON_ONE_POP_TRANSIT = ("p",)
_ON_ONE_POP_SEGMENTS = {
    ("a", "b"): 10.0, ("a", "p"): 10.0, ("b", "p"): 10.0,
    ("c", "d"): 10.0, ("c", "p"): 10.0, ("d", "p"): 10.0,
    ("a", "c"): 200.0,
}
PAST_ONE_POP_ARTIFACTS = fixtures.synthesis_over_segments(
    _ON_ONE_POP_SITES, _ON_ONE_POP_SEGMENTS, _ASKED_FOR, _ON_ONE_POP_TRANSIT
)


def test_the_floor_is_stated_over_the_circuit_that_keeps_one_pop_from_splitting_the_wan() -> None:
    assert round(
        PAST_ONE_POP_ARTIFACTS.synthesis.metrics.backbone_lower_bound_miles, 3
    ) == 240.0


def test_that_synthesis_runs_no_further_than_a_tenth_past_what_surviving_any_pop_takes() -> None:
    assert PAST_ONE_POP_ARTIFACTS.synthesis.metrics.physical_miles <= (
        1.1 * PAST_ONE_POP_ARTIFACTS.synthesis.metrics.backbone_lower_bound_miles
    )


def test_that_synthesis_is_split_by_the_loss_of_no_pop_it_runs_through() -> None:
    assert PAST_ONE_POP_ARTIFACTS.validation["backbone_mesh_has_no_cut_pop"]
