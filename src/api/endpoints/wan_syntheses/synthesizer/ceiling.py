from __future__ import annotations

import heapq
from dataclasses import dataclass, field

from synthesizer.graphs import reachable_over

_Node = tuple[str, str]
_Residual = dict[_Node, dict[_Node, int]]
_Miles = dict[_Node, dict[_Node, float]]
_Arc = tuple[_Node, _Node, int]
_NewArc = tuple[_Node, _Node, float, int]

_SINK: _Node = ("sink", "")


def _add_capacity(residual: _Residual, miles: _Miles, arc: _NewArc) -> None:
    tail, head, distance, units = arc
    residual.setdefault(tail, {})[head] = units
    residual.setdefault(head, {}).setdefault(tail, 0)
    miles.setdefault(tail, {})[head] = distance
    miles.setdefault(head, {})[tail] = -distance


def _unit_site_network(
    site: str,
    wan_pop_ids: tuple[str, ...],
    adjacency: dict[str, list[tuple[str, float]]],
) -> tuple[_Residual, _Miles, list[_Arc]]:
    peers = {peer for peer in wan_pop_ids if peer != site and peer in adjacency}
    new_arcs: list[_NewArc] = [
        (("in", city), ("out", city), 0.0, 1)
        for city in adjacency
        if city != site and city not in peers
    ]
    new_arcs += [
        (("out", city), ("in", neighbor), weight, 1)
        for city, neighbors in adjacency.items()
        for neighbor, weight in neighbors
    ]
    new_arcs += [
        (("in", peer), _SINK, 0.0, len(adjacency[peer])) for peer in sorted(peers)
    ]
    residual: _Residual = {}
    miles: _Miles = {}
    for arc in new_arcs:
        _add_capacity(residual, miles, arc)
    return residual, miles, [(tail, head, units) for tail, head, _distance, units in new_arcs]


def _shortest_runs(
    residual: _Residual,
    miles: _Miles,
    potential: dict[_Node, float],
    source: _Node,
) -> tuple[dict[_Node, float], dict[_Node, _Node | None]]:
    distance: dict[_Node, float] = {source: 0.0}
    reached: dict[_Node, _Node | None] = {source: None}
    settled: set[_Node] = set()
    queue: list[tuple[float, _Node]] = [(0.0, source)]
    while queue:
        spent, tail = heapq.heappop(queue)
        if tail in settled:
            continue
        settled.add(tail)
        for head, capacity in residual.get(tail, {}).items():
            if capacity <= 0 or head in settled:
                continue
            step = spent + miles[tail][head] + potential[tail] - potential[head]
            if head not in distance or step < distance[head]:
                distance[head] = step
                reached[head] = tail
                heapq.heappush(queue, (step, head))
    return distance, reached


def _augmenting_path(
    residual: _Residual,
    miles: _Miles,
    potential: dict[_Node, float],
    source: _Node,
) -> list[_Node] | None:
    distance, reached = _shortest_runs(residual, miles, potential, source)
    for end, run in distance.items():
        potential[end] += run
    if _SINK not in reached:
        return None
    path = [_SINK]
    cursor = reached[_SINK]
    while cursor is not None:
        path.append(cursor)
        cursor = reached[cursor]
    return path


def _spent_arcs(residual: _Residual, arcs: list[_Arc]) -> dict[_Node, list[_Node]]:
    spent: dict[_Node, list[_Node]] = {}
    for tail, head, units in arcs:
        spent.setdefault(tail, []).extend([head] * (units - residual[tail][head]))
    return spent


def _circuits_through(spent: dict[_Node, list[_Node]], source: _Node) -> list[tuple[str, ...]]:
    circuits: list[tuple[str, ...]] = []
    while spent.get(source):
        cities = [source[1]]
        cursor = spent[source].pop(0)
        while cursor != _SINK:
            side, city = cursor
            if side == "in":
                cities.append(city)
            cursor = spent[cursor].pop(0)
        circuits.append(tuple(cities))
    return circuits


def _proved_circuits(
    site: str,
    wan_pop_ids: tuple[str, ...],
    adjacency: dict[str, list[tuple[str, float]]],
) -> list[tuple[str, ...]]:
    residual, miles, arcs = _unit_site_network(site, wan_pop_ids, adjacency)
    source: _Node = ("out", site)
    potential: dict[_Node, float] = {end: 0.0 for end in (source, *residual)}
    while True:
        path = _augmenting_path(residual, miles, potential, source)
        if path is None:
            break
        for head, tail in zip(path, path[1:]):
            residual[tail][head] -= 1
            residual[head][tail] += 1
    return _circuits_through(_spent_arcs(residual, arcs), source)


@dataclass(frozen=True)
class CircuitProofInputs:
    wan_pop_ids: tuple[str, ...]
    adjacency: dict[str, list[tuple[str, float]]]
    terrestrial: dict[str, list[tuple[str, float]]] = field(default_factory=dict)


def _without_crossings_home(
    site: str, inputs: CircuitProofInputs, adjacency: dict[str, list[tuple[str, float]]]
) -> dict[str, list[tuple[str, float]]]:
    home = reachable_over(inputs.terrestrial).get(site, frozenset())
    on_land = {
        city: {neighbor for neighbor, _weight in neighbors}
        for city, neighbors in inputs.terrestrial.items()
    }
    kept = {
        city: [
            (neighbor, weight)
            for neighbor, weight in neighbors
            if neighbor not in home or neighbor in on_land.get(city, frozenset())
        ]
        for city, neighbors in adjacency.items()
    }
    return {city: neighbors for city, neighbors in kept.items() if neighbors}


def diverse_circuits(site: str, inputs: CircuitProofInputs) -> list[tuple[str, ...]]:
    return _proved_circuits(
        site, inputs.wan_pop_ids, _without_crossings_home(site, inputs, inputs.adjacency)
    )


def diverse_circuit_ceiling(site: str, inputs: CircuitProofInputs) -> int:
    return len(diverse_circuits(site, inputs))


def diverse_circuit_ceilings(inputs: CircuitProofInputs) -> dict[str, int]:
    return {
        site: diverse_circuit_ceiling(site, inputs)
        for site in inputs.wan_pop_ids
        if site in inputs.adjacency
    }
