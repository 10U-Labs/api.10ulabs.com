from __future__ import annotations

import math
from dataclasses import dataclass, replace
from itertools import combinations

from synthesizer.ceiling import CircuitProofInputs, diverse_circuits
from synthesizer.input_graph import FiberSegment, segment_key
from synthesizer.graphs import (
    articulation_points,
    build_adjacency,
    connected_components,
    dijkstra,
    fiber_segments_along,
    reachable_over,
    reconstruct_path,
    undirected_adjacency,
)
from synthesizer.model import (
    CIRCUIT_FOR_PIN,
    CIRCUIT_FOR_RELIEF,
    CIRCUIT_FOR_TARGET,
    SynthesisCircuit,
)
from synthesizer.survivable import CIRCUITS_SHARING_NO_POP, FiberInputs, select_fiber
from synthesizer.validation import diverse_circuit_count


def miles_along(
    pop_ids: tuple[str, ...],
    fiber_segments: dict[tuple[str, str], FiberSegment],
) -> float:
    return sum(
        fiber_segments[segment_key(pop_ids[index], pop_ids[index + 1])].distance_miles
        for index in range(len(pop_ids) - 1)
    )


@dataclass(frozen=True)
class WanPopConstraints:
    removed_pairs: frozenset[tuple[str, str]] = frozenset()
    number_of_diverse_circuits: int = 3
    forced_pairs: frozenset[tuple[str, str]] = frozenset()


@dataclass(frozen=True)
class BackboneMesh:
    circuits: list[SynthesisCircuit]
    lower_bound_miles: float


@dataclass(frozen=True)
class _DrawnFiber:
    wan_pop_ids: tuple[str, ...]
    distances: dict[str, dict[str, float]]
    selected: dict[tuple[str, str], FiberSegment]
    whole: dict[tuple[str, str], FiberSegment]
    constraints: WanPopConstraints


def _fiber_of(circuits: list[SynthesisCircuit]) -> tuple[set[str], set[tuple[str, str]]]:
    segments: set[tuple[str, str]] = set()
    for drawn_circuit in circuits:
        segments |= fiber_segments_along(drawn_circuit.pop_ids)
    return {city for segment in segments for city in segment}, segments


def _one_network(circuits: list[SynthesisCircuit], wan_pop_ids: tuple[str, ...]) -> bool:
    cities, segments = _fiber_of(circuits)
    return len(connected_components(cities | set(wan_pop_ids), segments)) == 1


def _cut_cities(
    circuits: list[SynthesisCircuit], wan_pop_ids: tuple[str, ...]
) -> set[str]:
    cities, segments = _fiber_of(circuits)
    return articulation_points(cities | set(wan_pop_ids), segments)


def _pieces_without_each(
    circuits: list[SynthesisCircuit], wan_pop_ids: tuple[str, ...]
) -> dict[str, int]:
    cities, segments = _fiber_of(circuits)
    sites = cities | set(wan_pop_ids)
    return {
        lost: len(connected_components(sites - {lost}, segments))
        for lost in sorted(sites)
    }


def _pinned_circuit(
    pair: tuple[str, str],
    fiber_segments: dict[tuple[str, str], FiberSegment],
) -> SynthesisCircuit | None:
    near, far = pair
    _distances, predecessors = dijkstra(build_adjacency(fiber_segments), near)
    pop_ids = reconstruct_path(near, far, predecessors)
    if not pop_ids:
        return None
    return SynthesisCircuit(
        "backbone_mesh", near, far, pop_ids,
        miles_along(pop_ids, fiber_segments), CIRCUIT_FOR_PIN,
    )


def _proved_over(
    site: str,
    fiber: dict[tuple[str, str], FiberSegment],
    drawn: _DrawnFiber,
) -> list[tuple[str, ...]]:
    constraints = drawn.constraints
    peers = tuple(
        peer
        for peer in drawn.wan_pop_ids
        if peer == site or segment_key(site, peer) not in constraints.removed_pairs
    )
    return sorted(
        diverse_circuits(site, CircuitProofInputs(peers, build_adjacency(fiber))),
        key=lambda pop_ids: (miles_along(pop_ids, fiber), pop_ids),
    )[: max(constraints.number_of_diverse_circuits, CIRCUITS_SHARING_NO_POP)]


def _diverse_circuits_of(site: str, drawn: _DrawnFiber) -> list[tuple[str, ...]]:
    return _proved_over(site, drawn.selected, drawn)


def _laid(drawn: _DrawnFiber, pinned: list[SynthesisCircuit]) -> list[SynthesisCircuit]:
    laid: dict[tuple[str, ...], SynthesisCircuit] = {
        min(drawn_circuit.pop_ids, drawn_circuit.pop_ids[::-1]): drawn_circuit
        for drawn_circuit in pinned
    }
    for site in sorted(drawn.wan_pop_ids):
        for pop_ids in _diverse_circuits_of(site, drawn):
            key = min(pop_ids, pop_ids[::-1])
            held = laid.get(key)
            if held is None:
                laid[key] = SynthesisCircuit(
                    "backbone_mesh", pop_ids[0], pop_ids[-1], pop_ids,
                    miles_along(pop_ids, drawn.whole), CIRCUIT_FOR_TARGET, (site,),
                )
            elif held.reason == CIRCUIT_FOR_TARGET and site not in held.requested_by:
                laid[key] = replace(
                    held, requested_by=tuple(sorted((*held.requested_by, site)))
                )
    return [laid[key] for key in sorted(laid)]


def _pairs_across(
    city: str, circuits: list[SynthesisCircuit], drawn: _DrawnFiber
) -> list[tuple[str, str]]:
    cities, segments = _fiber_of(circuits)
    sites = cities | set(drawn.wan_pop_ids)
    apart = {
        site: index
        for index, piece in enumerate(connected_components(sites - {city}, segments))
        for site in piece
    }
    sides: dict[int, list[str]] = {}
    for site in sorted(set(drawn.wan_pop_ids) - {city}):
        sides.setdefault(apart[site], []).append(site)
    split = sorted({apart[near] for near in undirected_adjacency(sites, segments)[city]})
    pairs = [
        (near, far)
        for left, right in combinations(split, 2)
        for near in sides.get(left, [])
        for far in sides.get(right, [])
    ]
    return sorted(
        pairs,
        key=lambda ends: (drawn.distances.get(ends[0], {}).get(ends[1], math.inf), ends),
    )


def _on_land(
    fiber: dict[tuple[str, str], FiberSegment]
) -> dict[tuple[str, str], FiberSegment]:
    return {key: segment for key, segment in fiber.items() if not segment.submarine}


def _circuit_around(
    city: str, circuits: list[SynthesisCircuit], drawn: _DrawnFiber
) -> SynthesisCircuit | None:
    fiber = {
        key: segment for key, segment in drawn.whole.items() if city not in key
    }
    land = _on_land(fiber)
    reach = reachable_over(build_adjacency(_on_land(drawn.whole)))
    for near, far in _pairs_across(city, circuits, drawn):
        joined = far in reach.get(near, frozenset())
        found = _pinned_circuit((near, far), land if joined else fiber)
        if found is None:
            continue
        return replace(found, reason=CIRCUIT_FOR_RELIEF)
    return None


def _relieved(circuits: list[SynthesisCircuit], drawn: _DrawnFiber) -> list[SynthesisCircuit]:
    relieved = list(circuits)
    beyond_help: set[str] = set()
    while True:
        cut = sorted(_cut_cities(relieved, drawn.wan_pop_ids) - beyond_help)
        if not cut:
            return relieved
        added = _circuit_around(cut[0], relieved, drawn)
        if added is None:
            beyond_help.add(cut[0])
            continue
        relieved.append(added)


def _needed(
    circuits: list[SynthesisCircuit], wan_pop_ids: tuple[str, ...], target: int
) -> list[SynthesisCircuit]:
    kept = list(circuits)
    held = {site: min(target, diverse_circuit_count(kept, site)) for site in wan_pop_ids}
    apart = _pieces_without_each(kept, wan_pop_ids)
    for spare in sorted(
        circuits, key=lambda drawn_circuit: (-drawn_circuit.distance_miles, drawn_circuit.pop_ids)
    ):
        if spare.reason == CIRCUIT_FOR_PIN:
            continue
        left = [drawn_circuit for drawn_circuit in kept if drawn_circuit is not spare]
        if any(
            min(target, diverse_circuit_count(left, site)) < held[site] for site in wan_pop_ids
        ):
            continue
        if not _one_network(left, wan_pop_ids):
            continue
        if any(
            pieces > apart[lost]
            for lost, pieces in _pieces_without_each(left, wan_pop_ids).items()
        ):
            continue
        kept = left
    return kept


def _selected_fiber(
    wan_pop_ids: tuple[str, ...],
    fiber_segments: dict[tuple[str, str], FiberSegment],
    constraints: WanPopConstraints,
) -> tuple[frozenset[tuple[str, str]], float, list[SynthesisCircuit]]:
    selection = select_fiber(FiberInputs(
        wan_pop_ids, fiber_segments, constraints.number_of_diverse_circuits
    ))
    drawn = (
        _pinned_circuit(pair, fiber_segments) for pair in sorted(constraints.forced_pairs)
    )
    pinned = [drawn_circuit for drawn_circuit in drawn if drawn_circuit is not None]
    segments = set(selection.segments)
    for drawn_circuit in pinned:
        segments |= fiber_segments_along(drawn_circuit.pop_ids)
    return frozenset(segments), selection.lower_bound_miles, pinned


def backbone_mesh(
    wan_pop_ids: tuple[str, ...],
    all_distances: dict[str, dict[str, float]],
    fiber_segments: dict[tuple[str, str], FiberSegment],
    constraints: WanPopConstraints = WanPopConstraints(),
) -> BackboneMesh:
    segments, floor, pinned = _selected_fiber(wan_pop_ids, fiber_segments, constraints)
    selected = {segment: fiber_segments[segment] for segment in sorted(segments)}
    drawn = _DrawnFiber(wan_pop_ids, all_distances, selected, fiber_segments, constraints)
    laid = _relieved(_laid(drawn, pinned), drawn)
    return BackboneMesh(
        _needed(laid, wan_pop_ids, constraints.number_of_diverse_circuits), floor
    )
