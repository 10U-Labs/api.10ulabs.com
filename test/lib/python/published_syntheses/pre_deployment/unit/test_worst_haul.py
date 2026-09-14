from typing import Any, Dict

from published_syntheses import site_from_row, worst_haul
from synthesizer.input_graph import Site

SOUTH: Dict[str, Any] = {"id": 1, "name": "South", "latitude": 40.0, "longitude": -100.0}
NORTH: Dict[str, Any] = {"id": 2, "name": "North", "latitude": 45.0, "longitude": -100.0}


def _site(name: str, latitude: float, exempt: bool) -> Dict[str, Any]:
    return {
        "id": 1, "name": name, "latitude": latitude, "longitude": -100.0,
        "exempt_from_distance_constraint": exempt,
    }


def _synthesis(*sites: Dict[str, Any]) -> Dict[str, Any]:
    return {"wan_pops": [SOUTH, NORTH], "sites": list(sites), "regions": []}


def _with_a_region(*regions: Dict[str, Any]) -> Dict[str, Any]:
    return {"wan_pops": [SOUTH, NORTH], "sites": [], "regions": list(regions)}


def test_a_published_row_is_rebuilt_as_the_site_it_places() -> None:
    assert site_from_row(SOUTH) == Site("1", "South", "", (40.0, -100.0))


def test_the_worst_haul_is_the_farthest_site_from_the_wan_pop_nearest_it() -> None:
    synthesis = _synthesis(
        _site("near", 41.0, False), _site("far", 43.0, False), _site("oconus", 10.0, True)
    )
    assert worst_haul(synthesis) == 138.2


def test_a_synthesis_whose_every_site_is_exempt_reads_zero() -> None:
    assert worst_haul(_synthesis(_site("oconus", 10.0, True))) == 0.0


def test_a_region_is_hauled_the_same_way_a_site_is() -> None:
    region = {"id": 1, "name": "region", "latitude": 43.0, "longitude": -100.0}
    assert worst_haul(_with_a_region(region)) == worst_haul(_synthesis(_site("s", 43.0, False)))
