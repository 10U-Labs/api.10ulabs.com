from __future__ import annotations

from collections.abc import Mapping

from synthesizer.flow_cuts import Separation, SeparationQuestion, weakest_separation
from synthesizer.input_graph import segment_key

_SITE = "a"
_ONE_PEER = frozenset({"b"})
_TWO_PEERS = frozenset({"b", "c"})
_NOTHING_SPARED: frozenset[str] = frozenset()
_NOTHING_BARRED: frozenset[tuple[str, str]] = frozenset()
_ARRIVING_AT_THE_PEER = frozenset({("a", "b")})
_ARRIVING_AT_THE_SITE = frozenset({("b", "a")})

_NOTHING_TO_SELECT = Separation(frozenset(), frozenset())
_ONLY_THE_SEGMENT = Separation(frozenset(), frozenset({("a", "b")}))
_ONLY_THE_CITY = Separation(frozenset({"x"}), frozenset())


def _whole(*segments: tuple[str, str]) -> dict[tuple[str, str], float]:
    return {segment_key(left, right): 1.0 for left, right in segments}


def _asked(
    held: Mapping[tuple[str, str], float],
    required: int,
    peers: frozenset[str] = _ONE_PEER,
    spared: frozenset[str] = _NOTHING_SPARED,
    barred: frozenset[tuple[str, str]] = _NOTHING_BARRED,
) -> Separation | None:
    return weakest_separation(
        SeparationQuestion(_SITE, peers, spared, held, barred), required
    )


_DIRECT = _whole(("a", "b"))

_PART_SELECTED: Mapping[tuple[str, str], float] = {("a", "b"): 0.5}
_UNSELECTED: Mapping[tuple[str, str], float] = {("a", "b"): 0.0}

_ELSEWHERE = _whole(("y", "z"))

_ROUND_ONE_CITY = _whole(("a", "x"), ("a", "p"), ("p", "x"), ("b", "x"), ("c", "x"))

_TWO_WAYS_TO_ONE_PEER = _whole(("a", "p"), ("p", "b"), ("a", "q"), ("q", "b"), ("b", "c"))


def test_fiber_already_carrying_what_was_asked_reports_no_separation() -> None:
    assert _asked(_DIRECT, 1) is None


def test_asking_for_nothing_ends_before_any_searching() -> None:
    assert _asked(_DIRECT, 0) is None


def test_a_site_the_fiber_does_not_reach_has_nothing_to_buy() -> None:
    assert _asked(_ELSEWHERE, 1) == _NOTHING_TO_SELECT


def test_two_sites_joined_by_one_segment_are_separated_by_that_segment() -> None:
    assert _asked(_DIRECT, 2) == _ONLY_THE_SEGMENT


def test_a_segment_held_in_part_carries_only_that_much_of_a_diverse_circuit() -> None:
    assert _asked(_PART_SELECTED, 1) == _ONLY_THE_SEGMENT


def test_a_segment_nothing_is_held_of_is_still_the_fiber_to_select() -> None:
    assert _asked(_UNSELECTED, 1) == _ONLY_THE_SEGMENT


def test_the_city_every_diverse_circuit_crosses_is_what_the_fiber_cannot_survive() -> None:
    assert _asked(_ROUND_ONE_CITY, 2, peers=_TWO_PEERS) == _ONLY_THE_CITY


def test_sparing_that_city_leaves_the_same_fiber_carrying_both_diverse_circuits() -> None:
    assert _asked(_ROUND_ONE_CITY, 2, peers=_TWO_PEERS, spared=frozenset({"x"})) is None


def test_a_peer_the_fiber_does_not_carry_is_left_out_of_the_count() -> None:
    assert _asked(_DIRECT, 1, peers=frozenset({"nowhere"})) == _NOTHING_TO_SELECT


def test_two_circuits_ending_at_one_peer_carry_two_ways_out() -> None:
    assert _asked(_TWO_WAYS_TO_ONE_PEER, 2, peers=_TWO_PEERS) is None


def test_a_circuit_ending_at_a_peer_and_one_crossing_it_carry_one_way_out() -> None:
    assert _asked(_whole(("a", "p"), ("p", "b"), ("b", "c")), 2, peers=_TWO_PEERS) == Separation(
        frozenset(), frozenset({("a", "p")})
    )


def test_an_arc_the_question_bars_carries_nothing_and_is_no_segment_to_select() -> None:
    assert _asked(_DIRECT, 1, barred=_ARRIVING_AT_THE_PEER) == _NOTHING_TO_SELECT


def test_barring_the_arc_the_other_way_leaves_the_circuit_carried() -> None:
    assert _asked(_DIRECT, 1, barred=_ARRIVING_AT_THE_SITE) is None
