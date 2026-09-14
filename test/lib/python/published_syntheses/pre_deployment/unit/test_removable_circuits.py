from typing import Any, Dict, List, Tuple

from published_syntheses import removable_circuits

IDS = {"west": 1, "east": 2, "north": 3, "south": 4, "up": 5, "down": 6, "deep": 7}


def _published_network(
    crossings: List[Tuple[str, ...]], forced: Tuple[Tuple[str, str], ...] = ()
) -> Dict[str, Any]:
    drawn = [
        {
            "source": IDS[cities[0]], "target": IDS[cities[-1]], "route": list(cities),
            "distance_miles": 100.0 * (len(cities) - 1),
        }
        for cities in crossings
    ]
    selected = sorted({end for cities in crossings for end in (cities[0], cities[-1])})
    return {
        "number_of_diverse_circuits": 2,
        "forced_circuits": [{"source": source, "target": target} for source, target in forced],
        "wan_pops": [{"id": IDS[city], "name": city} for city in selected],
        "circuits": drawn,
    }


SQUARE: List[Tuple[str, ...]] = [
    ("west", "a", "north"), ("north", "b", "east"), ("east", "d", "south"), ("south", "f", "west"),
]
SHORT_CROSSING: Tuple[str, ...] = ("west", "g", "east")
LONG_CROSSING: Tuple[str, ...] = ("west", "p", "q", "east")
HOMED_TWICE: List[Tuple[str, ...]] = [("west", "n", "deep"), ("east", "n", "deep")]
TRIANGLE: List[Tuple[str, ...]] = [
    ("west", "a", "north"), ("north", "b", "up"), ("up", "k", "west"),
]
FAR_TRIANGLE: List[Tuple[str, ...]] = [
    ("east", "d", "south"), ("south", "f", "down"), ("down", "m", "east"),
]
ONLY_CIRCUIT_BETWEEN_THEM: Tuple[str, ...] = ("west", "h", "east")
TWO_LOOPS: List[Tuple[str, ...]] = [
    ("west", "a", "north"), ("east", "e", "south"), ("north", "c", "east"), ("west", "c", "south"),
    ("west", "h", "east"),
]


def test_a_circuit_no_site_and_no_city_would_miss_is_reported_with_the_miles_it_runs() -> None:
    assert removable_circuits(_published_network(SQUARE + [SHORT_CROSSING])) == [
        ("west -> g -> east", 200.0)
    ]


def test_every_circuit_nobody_needs_is_reported_and_the_longest_of_them_first() -> None:
    assert removable_circuits(
        _published_network(SQUARE + [SHORT_CROSSING, LONG_CROSSING])
    ) == [("west -> p -> q -> east", 300.0), ("west -> g -> east", 200.0)]


def test_a_circuit_the_run_forced_is_kept_though_the_demands_would_let_it_go() -> None:
    assert not removable_circuits(
        _published_network(SQUARE + [SHORT_CROSSING], (("west", "east"),))
    )


def test_a_forced_pair_keeps_no_circuit_between_two_other_wan_pops() -> None:
    assert removable_circuits(
        _published_network(SQUARE + [SHORT_CROSSING], (("west", "north"),))
    ) == [("west -> g -> east", 200.0)]


def test_a_forced_pair_written_the_other_way_round_is_the_same_pair() -> None:
    assert not removable_circuits(
        _published_network(SQUARE + [SHORT_CROSSING], (("east", "west"),))
    )


def test_a_circuit_a_wan_pop_would_lose_a_diverse_circuit_by_is_kept() -> None:
    assert not removable_circuits(_published_network(TRIANGLE))


def test_a_circuit_holding_the_two_halves_of_a_backbone_together_is_kept() -> None:
    assert not removable_circuits(
        _published_network(TRIANGLE + FAR_TRIANGLE + [ONLY_CIRCUIT_BETWEEN_THEM])
    )


def test_a_circuit_whose_removal_would_leave_a_city_splitting_the_fiber_is_kept() -> None:
    assert not removable_circuits(_published_network(TWO_LOOPS))


def test_a_second_circuit_to_a_wan_pop_behind_one_city_is_kept_though_it_is_not_diverse() -> None:
    assert not removable_circuits(_published_network(SQUARE + HOMED_TWICE))


def test_fiber_that_already_splits_at_a_city_still_reports_a_circuit_nobody_needs() -> None:
    assert removable_circuits(
        _published_network(SQUARE + HOMED_TWICE + [SHORT_CROSSING])
    ) == [("west -> g -> east", 200.0)]


def test_a_network_carrying_no_circuits_reports_nothing() -> None:
    assert not removable_circuits(_published_network([]))
