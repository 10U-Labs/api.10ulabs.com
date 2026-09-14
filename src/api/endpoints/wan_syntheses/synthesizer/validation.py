from __future__ import annotations

from collections.abc import Callable, Mapping
from itertools import combinations

from synthesizer.input_graph import Site, segment_key
from synthesizer.model import (
    CIRCUIT_FOR_TARGET,
    Synthesis,
    SynthesisCircuit,
    MeshRequirements,
    ValidationReport,
)
from synthesizer.graphs import (
    articulation_points,
    connected_components,
    survives_any_one_segment_loss,
    survives_any_one_site_loss,
    fiber_segments_along,
)


def wan_pop_mesh_target(site: str, targets: MeshRequirements) -> int:
    ceilings = targets.ceilings
    if ceilings is None or site not in ceilings:
        return targets.number_of_diverse_circuits
    return min(targets.number_of_diverse_circuits, ceilings[site])


def backbone_mesh_deficient(
    wan_pop_ids: tuple[str, ...],
    wan_pop_degrees: dict[str, int],
    sites_by_id: dict[str, Site],
    targets: MeshRequirements,
) -> list[dict[str, object]]:
    if len(wan_pop_ids) <= targets.number_of_diverse_circuits:
        return []
    return [
        {"id": wan_pop_id, "name": sites_by_id[wan_pop_id].name, "degree": degree}
        for wan_pop_id, degree in sorted(wan_pop_degrees.items())
        if degree < wan_pop_mesh_target(wan_pop_id, targets)
        and wan_pop_id not in targets.degree_exempt
    ]


def synthesis_site_pairs(synthesis: Synthesis) -> set[tuple[str, str]]:
    pairs = set(synthesis.fiber_segment_keys)
    pairs.update(
        segment_key(homing_circuit.source, homing_circuit.target)
        for homing_circuit in synthesis.homings.joined()
    )
    return pairs

def included_site_ids(synthesis: Synthesis) -> set[str]:
    ids = set(synthesis.wan_pop_ids) | set(synthesis.transit_ids)
    ids.update(site_id for key in synthesis.fiber_segment_keys for site_id in key)
    ids.update(homing_circuit.source for homing_circuit in synthesis.homings.joined())
    ids.update(homing_circuit.target for homing_circuit in synthesis.homings.joined())
    return ids

def homes_by_site(synthesis: Synthesis) -> dict[str, set[str]]:
    homes: dict[str, set[str]] = {}
    for homing_circuit in synthesis.homings.joined():
        homes.setdefault(homing_circuit.source, set()).add(homing_circuit.target)
    return homes

def sites_below_homing_degree(synthesis: Synthesis, degree: int) -> list[str]:
    return [
        site_id
        for site_id, targets in sorted(homes_by_site(synthesis).items())
        if len(targets) != degree
    ]

def backbone_mesh_pairs(synthesis: Synthesis) -> set[tuple[str, str]]:
    return {
        segment_key(drawn_circuit.source, drawn_circuit.target)
        for drawn_circuit in synthesis.drawn_circuits
        if drawn_circuit.purpose == "backbone_mesh"
    }

def backbone_mesh_fiber_segments(synthesis: Synthesis) -> set[tuple[str, str]]:
    segments: set[tuple[str, str]] = set()
    for drawn_circuit in synthesis.drawn_circuits:
        if drawn_circuit.purpose == "backbone_mesh":
            segments |= fiber_segments_along(drawn_circuit.pop_ids)
    return segments

def _backbone_mesh_survives(
    synthesis: Synthesis, is_resilient: Callable[[set[str], set[tuple[str, str]]], bool]
) -> bool:
    ids = set(synthesis.wan_pop_ids)
    if len(ids) < 2:
        return True
    segments = backbone_mesh_fiber_segments(synthesis)
    sites = ids | {site for segment in segments for site in segment}
    return is_resilient(sites, segments)

def backbone_mesh_survives_any_one_link_loss(synthesis: Synthesis) -> bool:
    return _backbone_mesh_survives(synthesis, survives_any_one_segment_loss)

def backbone_mesh_survives_any_one_site_loss(synthesis: Synthesis) -> bool:
    return _backbone_mesh_survives(synthesis, survives_any_one_site_loss)

def backbone_mesh_pieces(synthesis: Synthesis) -> list[list[str]]:
    segments = backbone_mesh_fiber_segments(synthesis)
    wan_pops = frozenset(synthesis.wan_pop_ids)
    pops = {pop for segment in segments for pop in segment} | wan_pops
    pieces = {frozenset(piece) & wan_pops for piece in connected_components(pops, segments)}
    return sorted(sorted(piece) for piece in pieces - {frozenset[str]()})

def backbone_mesh_cut_pops(synthesis: Synthesis) -> list[str]:
    segments = backbone_mesh_fiber_segments(synthesis)
    pops = {pop for segment in segments for pop in segment}
    return sorted(articulation_points(pops, segments))

def circuits_out_of(
    drawn_circuits: list[SynthesisCircuit], site: str
) -> list[tuple[str, frozenset[str]]]:
    return [
        (
            drawn_circuit.target if drawn_circuit.source == site else drawn_circuit.source,
            frozenset(drawn_circuit.pop_ids) - {site},
        )
        for drawn_circuit in drawn_circuits
        if drawn_circuit.purpose == "backbone_mesh"
        and site in (drawn_circuit.source, drawn_circuit.target)
    ]


def _all_disjoint(circuits: tuple[tuple[str, frozenset[str]], ...]) -> bool:
    for (near_peer, near), (far_peer, far) in combinations(circuits, 2):
        shared = near & far
        if near_peer == far_peer:
            shared -= {near_peer}
        if shared:
            return False
    return True


def diverse_circuit_count(drawn_circuits: list[SynthesisCircuit], site: str) -> int:
    circuits = circuits_out_of(drawn_circuits, site)
    for size in range(len(circuits), 0, -1):
        if any(_all_disjoint(combo) for combo in combinations(circuits, size)):
            return size
    return 0


def backbone_mesh_independence_deficient(
    synthesis: Synthesis,
    sites_by_id: dict[str, Site],
    targets: MeshRequirements,
) -> list[dict[str, object]]:
    return [
        {
            "id": wan_pop_id,
            "name": sites_by_id[wan_pop_id].name,
            "independent_degree": degree,
        }
        for wan_pop_id, degree in sorted(
            (site, diverse_circuit_count(synthesis.drawn_circuits, site))
            for site in synthesis.wan_pop_ids
        )
        if degree < wan_pop_mesh_target(wan_pop_id, targets)
        and wan_pop_id not in targets.degree_exempt
    ]


def _ceilings_where(
    wan_pop_ids: tuple[str, ...],
    ceilings: Mapping[str, int] | None,
    keep: Callable[[int], bool],
) -> list[tuple[str, int]]:
    if ceilings is None:
        return []
    return [
        (site, ceilings[site])
        for site in sorted(wan_pop_ids)
        if site in ceilings and keep(ceilings[site])
    ]


def _ceiling_rows(
    wan_pop_ids: tuple[str, ...],
    sites_by_id: dict[str, Site],
    ceilings: Mapping[str, int] | None,
    keep: Callable[[int], bool],
) -> list[dict[str, object]]:
    return [
        {"id": site, "name": sites_by_id[site].name, "ceiling": ceiling}
        for site, ceiling in _ceilings_where(wan_pop_ids, ceilings, keep)
    ]


def diverse_circuit_ceilings_reported(
    wan_pop_ids: tuple[str, ...],
    sites_by_id: dict[str, Site],
    targets: MeshRequirements,
) -> list[dict[str, object]]:
    return [
        dict(row, target=wan_pop_mesh_target(str(row["id"]), targets))
        for row in _ceiling_rows(
            wan_pop_ids, sites_by_id, targets.ceilings, lambda _ceiling: True
        )
    ]


def ceiling_limited_wan_pops(
    wan_pop_ids: tuple[str, ...],
    sites_by_id: dict[str, Site],
    targets: MeshRequirements,
) -> list[dict[str, object]]:
    return _ceiling_rows(
        wan_pop_ids, sites_by_id, targets.ceilings,
        lambda value: value < targets.number_of_diverse_circuits,
    )


def mesh_circuits_out_of(synthesis: Synthesis, site: str) -> list[SynthesisCircuit]:
    return [
        drawn_circuit
        for drawn_circuit in synthesis.drawn_circuits
        if drawn_circuit.purpose == "backbone_mesh"
        and site in (drawn_circuit.source, drawn_circuit.target)
    ]


def unrequested_mesh_circuits(synthesis: Synthesis, site: str) -> list[dict[str, object]]:
    unrequested: list[dict[str, object]] = [
        {
            "peer": (
                drawn_circuit.target
                if drawn_circuit.source == site
                else drawn_circuit.source
            ),
            "reason": (
                "peer_target"
                if drawn_circuit.reason == CIRCUIT_FOR_TARGET
                else drawn_circuit.reason
            ),
        }
        for drawn_circuit in mesh_circuits_out_of(synthesis, site)
        if not (drawn_circuit.reason == CIRCUIT_FOR_TARGET and site in drawn_circuit.requested_by)
    ]
    return sorted(unrequested, key=lambda item: (str(item["peer"]), str(item["reason"])))


def above_target_wan_pops(
    synthesis: Synthesis,
    sites_by_id: dict[str, Site],
    targets: MeshRequirements,
) -> list[dict[str, object]]:
    asked_for = targets.number_of_diverse_circuits
    rows: list[dict[str, object]] = []
    for site in sorted(synthesis.wan_pop_ids):
        circuits = mesh_circuits_out_of(synthesis, site)
        if len(circuits) <= asked_for:
            continue
        rows.append({
            "id": site,
            "name": sites_by_id[site].name,
            "target": asked_for,
            "link_count": len(circuits),
            "diverse_circuit_count": diverse_circuit_count(synthesis.drawn_circuits, site),
            "unrequested_links": unrequested_mesh_circuits(synthesis, site),
        })
    return rows


def neighbor_degrees(
    ids: set[str], site_pairs: set[tuple[str, str]]
) -> dict[str, int]:
    neighbors: dict[str, set[str]] = {site_id: set() for site_id in ids}
    for left, right in site_pairs:
        if left in ids and right in ids:
            neighbors[left].add(right)
            neighbors[right].add(left)
    return {site_id: len(value) for site_id, value in neighbors.items()}

def validate_synthesis(
    sites: list[Site],
    synthesis: Synthesis,
    homing_degree: int = 2,
    targets: MeshRequirements = MeshRequirements(),
) -> ValidationReport:
    sites_by_id = {site.id: site for site in sites}
    ids = included_site_ids(synthesis)
    pairs = synthesis_site_pairs(synthesis)
    components = connected_components(ids, pairs)
    degrees = neighbor_degrees(ids, pairs)
    articulations = articulation_points(ids, pairs) if len(components) == 1 else set()
    missing_redundancy = sites_below_homing_degree(synthesis, homing_degree)
    wan_pop_degrees = neighbor_degrees(set(synthesis.wan_pop_ids), backbone_mesh_pairs(synthesis))
    mesh_deficient = backbone_mesh_deficient(
        synthesis.wan_pop_ids, wan_pop_degrees, sites_by_id, targets
    )
    independence_deficient = backbone_mesh_independence_deficient(
        synthesis, sites_by_id, targets
    )
    cut_pops = backbone_mesh_cut_pops(synthesis)

    return {
        "connected": len(components) == 1,
        "component_count": len(components),
        "min_distinct_neighbor_degree": min(degrees.values()) if degrees else 0,
        "degree_deficient_sites": [
            {"id": site_id, "name": sites_by_id[site_id].name, "degree": degree}
            for site_id, degree in sorted(degrees.items())
            if degree < 2
        ],
        "biconnected_no_articulation_points": len(components) == 1 and not articulations,
        "articulation_points": [
            {"id": site_id, "name": sites_by_id[site_id].name}
            for site_id in sorted(articulations)
        ],
        "every_site_meets_homing_degree": not missing_redundancy,
        "sites_below_homing_degree": [
            {"id": site_id, "name": sites_by_id[site_id].name}
            for site_id in missing_redundancy
        ],
        "backbone_meets_mesh_link_target": not mesh_deficient,
        "backbone_diverse_circuits_deficient": mesh_deficient,
        "backbone_meets_independent_mesh_link_target": not independence_deficient,
        "backbone_mesh_independence_deficient": independence_deficient,
        "backbone_degree_exempt": [
            {"id": wan_pop_id, "name": sites_by_id[wan_pop_id].name}
            for wan_pop_id in sorted(set(synthesis.wan_pop_ids) & targets.degree_exempt)
        ],
        "backbone_diverse_circuits_ceilings": diverse_circuit_ceilings_reported(
            synthesis.wan_pop_ids, sites_by_id, targets
        ),
        "backbone_diverse_circuits_ceiling_limited": ceiling_limited_wan_pops(
            synthesis.wan_pop_ids, sites_by_id, targets
        ),
        "backbone_diverse_circuits_above_target": above_target_wan_pops(
            synthesis, sites_by_id, targets
        ),
        "backbone_mesh_survives_any_one_link_loss":
            backbone_mesh_survives_any_one_link_loss(synthesis),
        "backbone_mesh_survives_any_one_site_loss":
            backbone_mesh_survives_any_one_site_loss(synthesis),
        "backbone_mesh_is_one_piece": len(backbone_mesh_pieces(synthesis)) <= 1,
        "backbone_mesh_pieces": [
            [{"id": pop, "name": sites_by_id[pop].name} for pop in piece]
            for piece in backbone_mesh_pieces(synthesis)
        ],
        "backbone_mesh_has_no_cut_pop": not cut_pops,
        "backbone_mesh_cut_pops": [
            {"id": pop, "name": sites_by_id[pop].name} for pop in cut_pops
        ],
    }
