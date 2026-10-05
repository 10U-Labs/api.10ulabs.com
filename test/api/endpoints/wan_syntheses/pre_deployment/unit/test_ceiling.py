from __future__ import annotations

import fixtures
from synthesizer.ceiling import (
    CircuitProofInputs,
    diverse_circuit_ceiling,
    diverse_circuits,
    diverse_circuit_ceilings,
)
from synthesizer.graphs import build_adjacency
from synthesizer.input_graph import FiberSegment

physical = fixtures.fiber_segments_from


def _miles_along(
    pop_ids: tuple[str, ...], adjacency: dict[str, list[tuple[str, float]]]
) -> float:
    return sum(
        weight
        for left, right in zip(pop_ids, pop_ids[1:])
        for neighbor, weight in adjacency[left]
        if neighbor == right
    )


_TWO_CUTS = build_adjacency(physical({
    ("bos", "alb"): 1.0, ("bos", "stm"): 1.0, ("bos", "x"): 1.0, ("x", "alb"): 1.0,
    ("alb", "n1"): 1.0, ("stm", "n2"): 1.0, ("n1", "n2"): 1.0,
}))
_TWO_CUT_BACKBONE = ("bos", "n1", "n2")


def test_the_ceiling_is_the_number_of_cuts_not_of_fiber_segments() -> None:
    assert diverse_circuit_ceiling("bos", CircuitProofInputs(_TWO_CUT_BACKBONE, _TWO_CUTS)) == 2


_ONE_CUT = build_adjacency(physical({
    ("bos", "alb"): 1.0, ("bos", "x"): 1.0, ("x", "alb"): 1.0,
    ("alb", "n1"): 1.0, ("alb", "n2"): 1.0, ("n1", "n2"): 1.0,
}))


def test_a_wan_pop_behind_one_failure_point_has_a_ceiling_of_one() -> None:
    assert diverse_circuit_ceiling(
        "bos", CircuitProofInputs(("bos", "n1", "n2"), _ONE_CUT)
    ) == 1


_TWIN_CIRCUITS = build_adjacency(physical({
    ("s", "p1"): 1.0, ("s", "p2"): 1.0, ("p1", "t"): 1.0, ("p2", "t"): 1.0,
    ("t", "u"): 1.0,
}))


def test_two_circuits_to_one_peer_sharing_no_pop_between_count_once() -> None:
    assert diverse_circuit_ceiling(
        "s", CircuitProofInputs(("s", "t", "u"), _TWIN_CIRCUITS)
    ) == 1


_ONE_PEER = ("s", "t")


def test_a_site_with_one_peer_has_a_ceiling_of_one_however_much_fiber_joins_them() -> None:
    assert diverse_circuit_ceiling("s", CircuitProofInputs(_ONE_PEER, _TWIN_CIRCUITS)) == 1


_THREE_CIRCUITS = build_adjacency(physical({
    ("s", "near"): 1.0, ("near", "t"): 1.0,
    ("s", "mid"): 2.0, ("mid", "t"): 2.0,
    ("s", "far"): 3.0, ("far", "t"): 3.0,
}))


def test_only_the_shortest_circuit_to_one_peer_is_proved() -> None:
    assert diverse_circuits("s", CircuitProofInputs(_ONE_PEER, _THREE_CIRCUITS)) == [
        ("s", "near", "t")
    ]


_TWO_WAYS_TO_ONE_PEER = build_adjacency(physical(fixtures.TWO_WAYS_TO_ONE_PEER_SEGMENTS))


def test_the_ceiling_credits_a_wan_pop_what_the_grader_credits_it_over_the_same_fiber() -> None:
    assert diverse_circuit_ceiling(
        "a", CircuitProofInputs(fixtures.TWO_WAYS_TO_ONE_PEER_WAN_POPS, _TWO_WAYS_TO_ONE_PEER)
    ) == fixtures.two_ways_to_one_peer_credited() == 1


def test_an_unreachable_wan_pop_has_no_ceiling_at_all() -> None:
    inputs = CircuitProofInputs(("nowhere", "n1", "n2"), _ONE_CUT)
    assert diverse_circuit_ceiling("nowhere", inputs) == 0


def test_the_ceilings_are_computed_for_every_wan_pop() -> None:
    assert diverse_circuit_ceilings(CircuitProofInputs(_TWO_CUT_BACKBONE, _TWO_CUTS)) == {
        "bos": 2, "n1": 2, "n2": 2
    }


_BOS_CIRCUITS = diverse_circuits("bos", CircuitProofInputs(_TWO_CUT_BACKBONE, _TWO_CUTS))


def test_the_counted_circuits_run_from_the_wan_pop_to_distinct_peers() -> None:
    assert sorted((pop_ids[0], pop_ids[-1]) for pop_ids in _BOS_CIRCUITS) == [
        ("bos", "n1"), ("bos", "n2")
    ]


def test_the_counted_circuits_share_no_intermediate_city() -> None:
    inner = [city for pop_ids in _BOS_CIRCUITS for city in pop_ids[1:-1]]
    assert sorted(inner) == sorted(set(inner))


_EXPRESS_SEGMENTS = build_adjacency(physical({
    ("sea", "hil"): 100.0, ("sea", "eug"): 100.0,
    ("sea", "pdx"): 1.0, ("pdx", "hil"): 1.0,
    ("sea", "tac"): 1.0, ("tac", "eug"): 1.0,
}))
_EXPRESS_BACKBONE = ("eug", "hil", "sea")


def test_the_two_shortest_circuits_proved_are_the_shortest_pair_there_is() -> None:
    assert sorted(
        _miles_along(pop_ids, _EXPRESS_SEGMENTS)
        for pop_ids in diverse_circuits(
            "sea", CircuitProofInputs(_EXPRESS_BACKBONE, _EXPRESS_SEGMENTS)
        )
    )[:2] == [2.0, 2.0]


def test_a_second_circuit_to_a_peer_is_never_proved() -> None:
    inputs = CircuitProofInputs(_EXPRESS_BACKBONE, _EXPRESS_SEGMENTS)
    assert diverse_circuit_ceiling("sea", inputs) == 2


_NEARER_TWICE = build_adjacency(physical({
    ("min", "max"): 1.0, ("max", "gtf"): 1.0,
    ("min", "ray"): 1.0, ("ray", "gtf"): 1.0,
    ("min", "bis"): 10.0, ("bis", "chy"): 10.0,
}))


def test_a_farther_distinct_peer_is_proved_before_a_nearer_peer_twice() -> None:
    assert sorted(
        pop_ids[-1]
        for pop_ids in diverse_circuits(
            "min", CircuitProofInputs(("chy", "gtf", "min"), _NEARER_TWICE)
        )
    ) == ["chy", "gtf"]


_PACIFIC_ADJACENCY = build_adjacency(physical(fixtures.CROSSING_SEGMENTS))
_PACIFIC_BACKBONE = ("eug", "hil", "sea")


def test_a_ceiling_counts_a_diverse_circuit_however_far_it_runs() -> None:
    assert diverse_circuit_ceiling(
        "sea", CircuitProofInputs(_PACIFIC_BACKBONE, _PACIFIC_ADJACENCY)
    ) == 2


_CHANGES_HANDS = fixtures.carrier_fiber_segments({
    ("s", "x"): (1.0, ("lumen",)),
    ("x", "t"): (1.0, ("zayo",)),
    ("s", "y"): (1.0, ("lumen",)),
    ("y", "u"): (1.0, ("zayo",)),
})
_ONE_COMPANY_EACH = fixtures.carrier_fiber_segments({
    ("s", "x"): (1.0, ("lumen",)),
    ("x", "t"): (1.0, ("lumen",)),
    ("s", "y"): (1.0, ("zayo",)),
    ("y", "u"): (1.0, ("zayo",)),
})


def _owned_proof(fiber: dict[tuple[str, str], FiberSegment]) -> CircuitProofInputs:
    return CircuitProofInputs(("s", "t"), build_adjacency(fiber))


def _two_peer_proof(fiber: dict[tuple[str, str], FiberSegment]) -> CircuitProofInputs:
    return CircuitProofInputs(("s", "t", "u"), build_adjacency(fiber))


def test_the_diverse_circuits_proved_may_each_change_hands() -> None:
    assert sorted(diverse_circuits("s", _two_peer_proof(_CHANGES_HANDS))) == [
        ("s", "x", "t"), ("s", "y", "u"),
    ]


def test_diverse_circuits_may_come_from_different_carriers() -> None:
    assert sorted(diverse_circuits("s", _two_peer_proof(_ONE_COMPANY_EACH))) == [
        ("s", "x", "t"), ("s", "y", "u"),
    ]


def test_the_same_fiber_joins_the_pair_when_nobody_owns_it() -> None:
    assert sorted(diverse_circuits("s", CircuitProofInputs(("s", "t", "u"), build_adjacency(
        physical({("s", "x"): 1.0, ("x", "t"): 1.0, ("s", "y"): 1.0, ("y", "u"): 1.0}),
    )))) == [("s", "x", "t"), ("s", "y", "u")]


_BOTH_HAVE_IT = fixtures.carrier_fiber_segments({("s", "t"): (1.0, ("lumen", "zayo"))})
_SHARE_A_CITY = fixtures.carrier_fiber_segments({
    ("s", "x"): (1.0, ("lumen", "zayo")),
    ("x", "t"): (1.0, ("lumen",)),
    ("x", "u"): (1.0, ("zayo",)),
    ("u", "t"): (1.0, ("zayo",)),
})


def test_a_circuit_both_carriers_have_is_drawn_once() -> None:
    assert diverse_circuits("s", _owned_proof(_BOTH_HAVE_IT)) == [("s", "t")]


def test_a_circuit_standing_on_a_city_already_spent_is_not_drawn() -> None:
    assert diverse_circuits("s", _owned_proof(_SHARE_A_CITY)) == [("s", "x", "t")]


_UNDER_WATER = fixtures.fiber_segments_under_water(
    {
        ("sea", "pdx"): 10.0, ("pdx", "hil"): 10.0,
        ("sea", "tok"): 1000.0, ("tok", "hil"): 1000.0,
    },
    {("sea", "tok"), ("tok", "hil")},
)
_UNDER_WATER_BACKBONE = ("hil", "sea")


def _on_land(
    fiber: dict[tuple[str, str], FiberSegment]
) -> dict[str, list[tuple[str, float]]]:
    return build_adjacency({
        key: segment for key, segment in fiber.items() if not segment.submarine
    })


def test_a_circuit_under_water_is_no_diverse_circuit_where_the_site_has_one_over_land() -> None:
    assert diverse_circuits(
        "sea",
        CircuitProofInputs(
            _UNDER_WATER_BACKBONE,
            build_adjacency(_UNDER_WATER),
            terrestrial=_on_land(_UNDER_WATER),
        ),
    ) == [("sea", "pdx", "hil")]


_ISLAND = fixtures.fiber_segments_under_water(
    {
        ("sea", "pdx"): 10.0, ("pdx", "hil"): 10.0,
        ("syd", "sea"): 8000.0, ("syd", "hil"): 8000.0,
    },
    {("syd", "sea"), ("syd", "hil")},
)
_ISLAND_BACKBONE = ("hil", "sea", "syd")


def test_a_site_reachable_only_over_water_keeps_the_diverse_circuits_it_has() -> None:
    assert sorted(diverse_circuits(
        "syd",
        CircuitProofInputs(
            _ISLAND_BACKBONE,
            build_adjacency(_ISLAND),
            terrestrial=_on_land(_ISLAND),
        ),
    )) == [("syd", "hil"), ("syd", "sea")]


_TWO_SHORES = fixtures.fiber_segments_under_water(
    {
        ("nyc", "phl"): 10.0, ("phl", "tpa"): 10.0,
        ("nyc", "atl"): 10.0, ("atl", "tpa"): 10.0,
        ("nyc", "lon"): 3000.0, ("lon", "mol"): 10.0,
    },
    {("nyc", "lon")},
)
_TWO_SHORES_BACKBONE = ("mol", "nyc", "tpa")


def test_a_site_joined_over_land_to_one_peer_is_proved_a_crossing_to_another() -> None:
    assert sorted(
        pop_ids[-1]
        for pop_ids in diverse_circuits(
            "nyc",
            CircuitProofInputs(
                _TWO_SHORES_BACKBONE,
                build_adjacency(_TWO_SHORES),
                terrestrial=_on_land(_TWO_SHORES),
            ),
        )
    ) == ["mol", "tpa"]


_ALREADY_NEEDED_PROOF = CircuitProofInputs(
    fixtures.ALREADY_NEEDED_SITES, build_adjacency(fixtures.ALREADY_NEEDED_FIBER)
)


def test_a_wan_pop_is_proved_a_circuit_that_changes_hands() -> None:
    assert sorted(diverse_circuits("b", _ALREADY_NEEDED_PROOF)) == [
        ("b", "c", "d"), ("b", "e", "f"),
    ]


def test_every_diverse_circuit_a_wan_pops_fiber_carries_is_proved() -> None:
    assert diverse_circuit_ceiling("b", CircuitProofInputs(
        fixtures.FLOORED_ABOVE_SITES,
        build_adjacency(fixtures.carrier_fiber_segments(fixtures.FLOORED_ABOVE_SEGMENTS)),
    )) == 3
