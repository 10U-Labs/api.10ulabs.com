from __future__ import annotations

from itertools import combinations
from typing import Any, Callable

from synthesizer.input_graph import Site, haversine_miles

Read = Callable[[str], Any]
COLLECTION = "/wan-syntheses"
UNFINISHED = frozenset({"creating", "synthesizing"})
PARTS = ("wan-pops", "backbone-circuits", "homing-circuits", "fiber-segments")
INPUTS = ("sites", "hyperscale-cloud-service-provider-regions")


def _latest(read: Read, label: str) -> int | None:
    ids: list[int] = [run["id"] for run in read(COLLECTION) if run["label"] == label]
    return max(ids, default=None)


def published_synthesis(read: Read, label: str, config: dict[str, Any]) -> dict[str, Any]:
    synthesis_id = _latest(read, label)
    record: dict[str, Any] = {} if synthesis_id is None else read(f"{COLLECTION}/{synthesis_id}")
    under = f"{COLLECTION}/{synthesis_id}"
    given = {part: read(f"{under}/{part}") for part in INPUTS} if record else {}
    published = (
        {part: read(f"{under}/{part}") for part in PARTS} if record.get("status") == "success"
        else {}
    )
    backbone = config["backbone"]
    return {
        "label": label,
        "id": synthesis_id,
        "target_miles": backbone["coverage_target_miles"],
        "number_of_diverse_circuits": backbone["number_of_diverse_circuits"],
        "homing_degree": config["homing"]["degree"],
        "max_wan_pop_count": backbone["wan_pop_count"]["max"],
        "forced": backbone.get("forced", {}).get("wan_pops", []),
        "forced_circuits": backbone.get("forced", {}).get("circuits", []),
        "status": record,
        "lower_bound_miles": record.get("backbone_lower_bound_miles"),
        "wan_pops": published.get("wan-pops", []),
        "sites": given.get("sites", []),
        "regions": given.get("hyperscale-cloud-service-provider-regions", []),
        "circuits": published.get("backbone-circuits", []),
        "homings": published.get("homing-circuits", []),
        "fiber": published.get("fiber-segments", []),
    }


def site_from_row(row: dict[str, Any]) -> Site:
    return Site(str(row["id"]), row["name"], "", (row["latitude"], row["longitude"]))


def homed_rows(synthesis: dict[str, Any]) -> list[dict[str, Any]]:
    sites: list[dict[str, Any]] = synthesis["sites"]
    regions: list[dict[str, Any]] = synthesis["regions"]
    return sites + regions


def worst_haul(synthesis: dict[str, Any]) -> float:
    wan_pop_sites = [site_from_row(row) for row in synthesis["wan_pops"]]
    hauls: list[float] = [
        min(haversine_miles(site_from_row(row), site) for site in wan_pop_sites)
        for row in homed_rows(synthesis)
        if not row.get("exempt_from_distance_constraint", False)
    ]
    return round(max(hauls, default=0.0), 1)


def wan_pop_names(synthesis: dict[str, Any]) -> dict[int, str]:
    return {row["id"]: row["name"] for row in synthesis["wan_pops"]}


def _circuits_out_of(
    circuits: list[dict[str, Any]], wan_pop: int, names: dict[int, str]
) -> list[tuple[str, frozenset[str]]]:
    return [
        (
            names[circuit["target"] if circuit["source"] == wan_pop else circuit["source"]],
            frozenset(circuit["route"]) - {names[wan_pop]},
        )
        for circuit in circuits
        if wan_pop in (circuit["source"], circuit["target"])
    ]


def _fail_apart(circuits: tuple[tuple[str, frozenset[str]], ...]) -> bool:
    return all(
        not ((near & far) - ({peer} if peer == other else frozenset()))
        for (peer, near), (other, far) in combinations(circuits, 2)
    )


def diverse_circuit_count(
    circuits: list[dict[str, Any]], wan_pop: int, names: dict[int, str]
) -> int:
    out_of_wan_pop = _circuits_out_of(circuits, wan_pop, names)
    return max(
        (
            size
            for size in range(1, len(out_of_wan_pop) + 1)
            if any(_fail_apart(combo) for combo in combinations(out_of_wan_pop, size))
        ),
        default=0,
    )


def overbuilt_pairs(synthesis: dict[str, Any]) -> list[tuple[str, int]]:
    drawn: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for drawn_circuit in synthesis["circuits"]:
        pair = (
            min(drawn_circuit["source"], drawn_circuit["target"]),
            max(drawn_circuit["source"], drawn_circuit["target"]),
        )
        drawn.setdefault(pair, []).append(drawn_circuit)
    names = wan_pop_names(synthesis)
    asked = synthesis["number_of_diverse_circuits"]
    apart = pieces_without_each(synthesis["circuits"])
    overbuilt: list[tuple[str, int]] = []
    for pair, circuits in sorted(drawn.items()):
        if len(circuits) < 2:
            continue
        spare = max(circuits, key=lambda circuit: circuit["distance_miles"])
        kept = [circuit for circuit in synthesis["circuits"] if circuit is not spare]
        if _cuts_deeper(kept, apart):
            continue
        if not any(
            diverse_circuit_count(kept, end, names)
            < min(asked, diverse_circuit_count(synthesis["circuits"], end, names))
            for end in pair
        ):
            overbuilt.append((" <-> ".join(sorted(names[end] for end in pair)), len(circuits)))
    return overbuilt


def _joined_to(pairs: list[tuple[str, str]]) -> dict[str, set[str]]:
    joined: dict[str, set[str]] = {}
    for near, far in pairs:
        joined.setdefault(near, set()).add(far)
        joined.setdefault(far, set()).add(near)
    return joined


def _reached(joined: dict[str, set[str]], start: str) -> set[str]:
    found = {start}
    unswept = [start]
    while unswept:
        here = unswept.pop()
        for there in joined[here] - found:
            found.add(there)
            unswept.append(there)
    return found


def _all_one_network(joined: dict[str, set[str]]) -> bool:
    return all(_reached(joined, start) == set(joined) for start in sorted(joined)[:1])


def _pieces(joined: dict[str, set[str]]) -> int:
    unplaced = set(joined)
    counted = 0
    while unplaced:
        unplaced -= _reached(joined, min(unplaced))
        counted += 1
    return counted


def pieces_without_each(circuits: list[dict[str, Any]]) -> dict[str, int]:
    joined = _cities_the_circuits_cross(circuits)
    return {
        lost: _pieces({
            city: reached - {lost} for city, reached in joined.items() if city != lost
        })
        for lost in joined
    }


def _cuts_deeper(kept: list[dict[str, Any]], apart: dict[str, int]) -> bool:
    return any(pieces > apart[lost] for lost, pieces in pieces_without_each(kept).items())


def cut_cities(circuits: list[dict[str, Any]]) -> list[str]:
    whole = _pieces(_cities_the_circuits_cross(circuits))
    return sorted(
        lost for lost, pieces in pieces_without_each(circuits).items() if pieces > whole
    )


def _wan_pops_the_circuits_join(
    circuits: list[dict[str, Any]], names: dict[int, str]
) -> dict[str, set[str]]:
    alone: dict[str, set[str]] = {name: set() for name in names.values()}
    return alone | _joined_to(
        [(names[circuit["source"]], names[circuit["target"]]) for circuit in circuits]
    )


def _cities_the_circuits_cross(circuits: list[dict[str, Any]]) -> dict[str, set[str]]:
    return _joined_to([
        (near, far)
        for circuit in circuits
        for near, far in zip(circuit["route"], circuit["route"][1:])
    ])


def removable_circuits(synthesis: dict[str, Any]) -> list[tuple[str, float]]:
    names = wan_pop_names(synthesis)
    asked = synthesis["number_of_diverse_circuits"]
    pinned = {
        frozenset((pair["source"], pair["target"])) for pair in synthesis["forced_circuits"]
    }
    held_diverse_circuits = {
        wan_pop: min(asked, diverse_circuit_count(synthesis["circuits"], wan_pop, names))
        for wan_pop in names
    }
    apart = pieces_without_each(synthesis["circuits"])
    removable: list[tuple[str, float]] = []
    for spare in synthesis["circuits"]:
        if frozenset((names[spare["source"]], names[spare["target"]])) in pinned:
            continue
        kept = [circuit for circuit in synthesis["circuits"] if circuit is not spare]
        if any(
            diverse_circuit_count(kept, wan_pop, names) < held_diverse_circuits[wan_pop]
            for wan_pop in names
        ):
            continue
        if not _all_one_network(_wan_pops_the_circuits_join(kept, names)):
            continue
        if _cuts_deeper(kept, apart):
            continue
        removable.append((" -> ".join(spare["route"]), spare["distance_miles"]))
    return sorted(removable, key=lambda found: (-found[1], found[0]))


def _spot(row: dict[str, Any], end: str = "") -> str:
    return f"{row[f'{end}latitude']},{row[f'{end}longitude']}"


def wan_pop_groups(synthesis: dict[str, Any]) -> list[list[str]]:
    joined: dict[str, set[str]] = {_spot(row): set() for row in synthesis["wan_pops"]}
    joined |= _joined_to([
        (_spot(entry, "a_"), _spot(entry, "z_")) for entry in synthesis["fiber"]
    ])
    unplaced = {_spot(row): row["name"] for row in synthesis["wan_pops"]}
    groups: list[list[str]] = []
    while unplaced:
        reached = _reached(joined, min(unplaced))
        groups.append(sorted(unplaced[spot] for spot in unplaced.keys() & reached))
        unplaced = {spot: name for spot, name in unplaced.items() if spot not in reached}
    return groups


def fiber_miles_run_over(synthesis: dict[str, Any]) -> float:
    segments: list[float] = [entry["distance_miles"] for entry in synthesis["fiber"]]
    return sum(segments)


def homed_counts(synthesis: dict[str, Any]) -> dict[tuple[str, int], int]:
    homed: dict[tuple[str, int], int] = {}
    for circuit in synthesis["homings"]:
        key = (circuit["homing_kind"], circuit["source_id"])
        homed[key] = homed.get(key, 0) + 1
    return homed


KIND_OF = {"tenant_to_backbone": "tenant", "provider_to_backbone": "provider"}


def homing_miles_served(synthesis: dict[str, Any], kind: str) -> float:
    miles: list[float] = [
        circuit["distance_miles"]
        for circuit in synthesis["homings"]
        if KIND_OF[circuit["homing_kind"]] == kind
    ]
    return sum(miles)
