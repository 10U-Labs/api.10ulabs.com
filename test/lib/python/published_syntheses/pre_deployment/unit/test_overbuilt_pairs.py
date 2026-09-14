from typing import Any, Dict, List

from published_syntheses import diverse_circuit_count, overbuilt_pairs

IDS = {"west": 1, "east": 2, "north": 3, "south": 4}


def _circuit(source: str, target: str, *transit: str) -> Dict[str, Any]:
    return {
        "source": IDS[source], "target": IDS[target], "route": [source, *transit, target],
        "distance_miles": 100.0 * (len(transit) + 1),
    }


def _synthesis(circuits: List[Dict[str, Any]], allowed: int = 2) -> Dict[str, Any]:
    ends = sorted({circuit[end] for circuit in circuits for end in ("source", "target")})
    names = {wan_pop: name for name, wan_pop in IDS.items()}
    return {
        "number_of_diverse_circuits": allowed,
        "wan_pops": [{"id": wan_pop, "name": names[wan_pop]} for wan_pop in ends],
        "circuits": circuits,
    }


SPARE_CIRCUIT = [
    _circuit("west", "east", "m1"), _circuit("west", "east", "m2"),
    _circuit("west", "north", "m3"), _circuit("east", "north", "m4"),
]


def test_a_pair_holding_a_circuit_neither_end_needs_is_reported_with_its_count() -> None:
    assert overbuilt_pairs(_synthesis(SPARE_CIRCUIT)) == [("east <-> west", 2)]


def test_a_pair_whose_second_circuit_is_a_diverse_circuit_is_not_reported() -> None:
    synthesis = _synthesis([_circuit("west", "east", "m1"), _circuit("west", "east", "m2")])
    assert not overbuilt_pairs(synthesis)


def test_a_second_circuit_crossing_the_same_city_as_the_first_is_reported() -> None:
    synthesis = _synthesis([
        _circuit("west", "east", "m1"), _circuit("west", "east", "m1", "x"),
        _circuit("west", "north", "m3"), _circuit("east", "north", "m4"),
    ])
    assert overbuilt_pairs(synthesis) == [("east <-> west", 2)]


ROUND_A_CUT_CITY = [
    _circuit("east", "north", "m2"), _circuit("west", "north", "m2", "m3"),
    _circuit("east", "west", "m3"), _circuit("west", "north", "m3"),
]


def test_a_second_circuit_holding_a_pop_from_splitting_the_wan_is_not_reported() -> None:
    assert not overbuilt_pairs(_synthesis(ROUND_A_CUT_CITY))


ONE_END_COUNTS_IT = [
    _circuit("north", "south", "m1"), _circuit("north", "west", "m6"),
    _circuit("west", "north", "m4"), _circuit("west", "south", "m1", "m4"),
]


def test_a_second_circuit_an_end_counts_among_its_own_is_not_reported() -> None:
    assert not overbuilt_pairs(_synthesis(ONE_END_COUNTS_IT))


def test_a_pair_joined_once_is_not_reported() -> None:
    assert not overbuilt_pairs(_synthesis([_circuit("west", "east", "m1")]))


def test_circuits_served_under_either_order_of_the_two_ends_count_as_one_pair() -> None:
    synthesis = _synthesis([
        _circuit("west", "east", "m1"), _circuit("east", "west", "m2"),
        _circuit("west", "east", "m5"), _circuit("west", "north", "m3"),
        _circuit("east", "north", "m4"),
    ])
    assert overbuilt_pairs(synthesis) == [("east <-> west", 3)]


def test_circuits_between_different_pairs_are_counted_apart() -> None:
    synthesis = _synthesis([_circuit("west", "east", "m1"), _circuit("west", "north", "m3")])
    assert not overbuilt_pairs(synthesis)


def test_every_overbuilt_pair_is_reported_not_only_the_first() -> None:
    synthesis = _synthesis([
        *SPARE_CIRCUIT, _circuit("north", "south", "m6"), _circuit("north", "south", "m7"),
        _circuit("west", "south", "m8"),
    ])
    assert [pair for pair, _count in overbuilt_pairs(synthesis)] == [
        "east <-> west", "north <-> south"
    ]


def test_a_network_carrying_no_circuits_reports_nothing() -> None:
    assert not overbuilt_pairs(_synthesis([]))


def test_a_wan_pop_s_diverse_circuits_are_the_most_that_share_no_city_between() -> None:
    synthesis = _synthesis(SPARE_CIRCUIT)
    names = {wan_pop: name for name, wan_pop in IDS.items()}
    assert diverse_circuit_count(synthesis["circuits"], IDS["west"], names) == 3
