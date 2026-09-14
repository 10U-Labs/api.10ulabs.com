from __future__ import annotations

from synthesizer.input_graph import Site, haversine_miles
from synthesizer.model import ForcedCircuits


def _pairs_within(
    wan_pop_set: set[str], pairs: frozenset[tuple[str, str]]
) -> frozenset[tuple[str, str]]:
    return frozenset(
        pair for pair in pairs if pair[0] in wan_pop_set and pair[1] in wan_pop_set
    )


def removed_backbone_pairs(
    wan_pop_set: set[str], circuits: ForcedCircuits
) -> frozenset[tuple[str, str]]:
    return _pairs_within(wan_pop_set, circuits.removed_backbone)


def forced_backbone_pairs(
    wan_pop_set: set[str], circuits: ForcedCircuits
) -> frozenset[tuple[str, str]]:
    return _pairs_within(wan_pop_set, circuits.backbone)


def apply_forced_homes(
    site: Site,
    completed: list[str],
    circuits: ForcedCircuits,
    pop_by_id: dict[str, Site],
    homes: int,
) -> list[str]:
    required = [wan_pop for homed, wan_pop in sorted(circuits.homes) if homed == site.id]
    if not required:
        return completed
    nearest = sorted(
        (home for home in completed if home not in required),
        key=lambda home: haversine_miles(site, pop_by_id[home]),
    )
    return (required + nearest)[:homes]
