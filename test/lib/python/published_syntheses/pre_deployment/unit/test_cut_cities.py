from typing import Any, Dict, List, Tuple

from published_syntheses import cut_cities


def _published_circuits(crossings: List[Tuple[str, ...]]) -> List[Dict[str, Any]]:
    return [{"route": list(cities)} for cities in crossings]


RING = _published_circuits([
    ("west", "a", "north"), ("north", "b", "east"), ("east", "d", "south"), ("south", "f", "west"),
])
BOWTIE = _published_circuits([
    ("west", "a", "waist"), ("waist", "b", "west"), ("east", "c", "waist"), ("waist", "d", "east"),
])
CHAIN = _published_circuits([("west", "middle", "centre", "east")])
APART = _published_circuits([
    ("west", "a", "north"), ("north", "b", "west"), ("east", "c", "south"), ("south", "d", "east"),
])
APART_AT_A_WAIST = _published_circuits([
    ("west", "a", "waist"), ("waist", "b", "west"), ("waist", "c", "north"),
    ("north", "d", "waist"), ("east", "e", "south"), ("south", "f", "east"),
])


def test_a_network_no_city_carries_names_nobody() -> None:
    assert cut_cities(RING) == []


def test_a_network_one_city_holds_together_names_that_city() -> None:
    assert cut_cities(BOWTIE) == ["waist"]


def test_a_network_two_cities_hold_together_names_both_of_them() -> None:
    assert cut_cities(CHAIN) == ["centre", "middle"]


def test_a_network_in_pieces_that_no_city_cuts_deeper_names_nobody() -> None:
    assert cut_cities(APART) == []


def test_a_network_in_pieces_still_names_the_city_that_cuts_a_piece_deeper() -> None:
    assert cut_cities(APART_AT_A_WAIST) == ["waist"]
