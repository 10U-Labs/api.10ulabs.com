from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from itertools import combinations

from synthesizer.flow_cuts import Separation, SeparationQuestion, weakest_separation
from synthesizer.graphs import build_adjacency, reachable_over
from synthesizer.input_graph import FiberSegment
from synthesizer.linear_program import GrowingSegmentProgram, SegmentRow, SegmentSelection

_HELD_OUTRIGHT = 0.5

_TOLERANCE = 1e-6

CIRCUITS_SHARING_NO_POP = 2


@dataclass(frozen=True)
class FiberInputs:
    wan_pop_ids: tuple[str, ...]
    fiber_segments: Mapping[tuple[str, str], FiberSegment]
    number_of_diverse_circuits: int = 3


@dataclass(frozen=True)
class FiberSelection:
    segments: frozenset[tuple[str, str]]
    lower_bound_miles: float


@dataclass(frozen=True)
class _Requirement:
    site: str
    peers: frozenset[str]
    spared: frozenset[str]
    required: int
    barred: frozenset[tuple[str, str]]


@dataclass(frozen=True)
class _Writing:
    inputs: FiberInputs
    whole: Mapping[tuple[str, str], float]
    crossings: frozenset[tuple[str, str]]
    shores: Mapping[str, frozenset[str]]


@dataclass
class _Search:
    order: list[tuple[str, str]]
    column: dict[tuple[str, str], int]
    program: GrowingSegmentProgram
    written: set[tuple[tuple[int, ...], float]]
    selected: frozenset[tuple[str, str]]


def _question(
    requirement: _Requirement, held: Mapping[tuple[str, str], float]
) -> SeparationQuestion:
    return SeparationQuestion(
        requirement.site,
        requirement.peers,
        requirement.spared,
        held,
        requirement.barred,
    )


def _carried(requirement: _Requirement, whole: Mapping[tuple[str, str], float]) -> int:
    required = requirement.required
    while required > 0 and weakest_separation(_question(requirement, whole), required):
        required -= 1
    return required


def _lowered(
    rows: list[_Requirement], whole: Mapping[tuple[str, str], float]
) -> list[_Requirement]:
    carried = [replace(row, required=_carried(row, whole)) for row in rows]
    return [row for row in carried if row.required]


def _shore_of(site: str, writing: _Writing) -> frozenset[str]:
    return writing.shores.get(site, frozenset({site}))


def _arriving_on(shore: frozenset[str], writing: _Writing) -> frozenset[tuple[str, str]]:
    return frozenset(
        (away, home)
        for left, right in writing.crossings
        for away, home in ((left, right), (right, left))
        if home in shore
    )


def _diverse_circuits_out_of(site: str, writing: _Writing) -> list[_Requirement]:
    peers = frozenset(writing.inputs.wan_pop_ids) - {site}
    return _lowered(
        [
            _Requirement(
                site,
                peers,
                frozenset({site}),
                max(writing.inputs.number_of_diverse_circuits, CIRCUITS_SHARING_NO_POP),
                _arriving_on(_shore_of(site, writing), writing),
            )
        ],
        writing.whole,
    )


def _barred_between(near: str, writing: _Writing) -> frozenset[tuple[str, str]]:
    shore = _shore_of(near, writing)
    if shore.issuperset(writing.inputs.wan_pop_ids):
        return _arriving_on(shore, writing)
    return frozenset()


def _two_circuits_sharing_no_pop(writing: _Writing) -> list[_Requirement]:
    asked = [
        _Requirement(
            near,
            frozenset({far}),
            frozenset({near, far}),
            CIRCUITS_SHARING_NO_POP,
            _barred_between(near, writing),
        )
        for near, far in combinations(sorted(writing.inputs.wan_pop_ids), 2)
    ]
    return asked if asked == _lowered(asked, writing.whole) else []


def _writing(inputs: FiberInputs, fiber: Mapping[tuple[str, str], float]) -> _Writing:
    on_land = {
        key: segment
        for key, segment in inputs.fiber_segments.items()
        if not segment.submarine
    }
    return _Writing(
        inputs,
        {segment: 1.0 for segment in fiber},
        frozenset(segment for segment in fiber if segment not in on_land),
        reachable_over(build_adjacency(on_land)),
    )


def _shortfalls(
    requirements: list[_Requirement], held: Mapping[tuple[str, str], float]
) -> list[tuple[Separation, int]]:
    found: list[tuple[Separation, int]] = []
    for requirement in requirements:
        separation = weakest_separation(_question(requirement, held), requirement.required)
        if separation is not None:
            found.append((separation, requirement.required))
    return found


def _rows(
    shortfalls: list[tuple[Separation, int]], column: Mapping[tuple[str, str], int]
) -> list[SegmentRow]:
    return [
        SegmentRow(
            tuple(sorted(column[segment] for segment in separation.crossing_segments)),
            float(required - len(separation.lost_cities)),
        )
        for separation, required in shortfalls
    ]


def _held(
    fiber: Mapping[tuple[str, str], float], selected: frozenset[tuple[str, str]]
) -> dict[tuple[str, str], float]:
    return {segment: 1.0 if segment in selected else 0.0 for segment in fiber}


def _shares(
    selection: SegmentSelection, order: list[tuple[str, str]]
) -> dict[tuple[str, str], float]:
    return dict(zip(order, selection.held))


def _write(search: _Search, rows: list[SegmentRow]) -> bool:
    fresh = []
    for row in rows:
        already = (row.columns, row.floor)
        if already not in search.written:
            search.written.add(already)
            fresh.append(row)
    search.program.add_rows(tuple(fresh))
    return bool(fresh)


def _solve_search(search: _Search) -> SegmentSelection:
    search.program.hold_whole(
        frozenset(search.column[segment] for segment in search.selected)
    )
    return search.program.solve()


def _tighten(search: _Search, requirements: list[_Requirement]) -> SegmentSelection:
    selection = _solve_search(search)
    shortfalls = _shortfalls(requirements, _shares(selection, search.order))
    while shortfalls and _write(search, _rows(shortfalls, search.column)):
        selection = _solve_search(search)
        shortfalls = _shortfalls(requirements, _shares(selection, search.order))
    return selection


def _round_up(search: _Search, selection: SegmentSelection) -> frozenset[tuple[str, str]]:
    shares = _shares(selection, search.order)
    left = [
        (share, segment) for segment, share in shares.items() if segment not in search.selected
    ]
    fresh = frozenset(
        segment for share, segment in left if share >= _HELD_OUTRIGHT - _TOLERANCE
    )
    return fresh or frozenset({max(left)[1]})


def _search_over(
    fiber: Mapping[tuple[str, str], float], order: list[tuple[str, str]]
) -> _Search:
    return _Search(
        order,
        {segment: index for index, segment in enumerate(order)},
        GrowingSegmentProgram(tuple(fiber[segment] for segment in order)),
        set(),
        frozenset(),
    )


def _answered_by_every_wan(writing: _Writing) -> list[_Requirement]:
    asked = [
        row
        for site in writing.inputs.wan_pop_ids
        for row in _diverse_circuits_out_of(site, writing)
    ]
    return asked + _two_circuits_sharing_no_pop(writing)


def _floor_under(
    requirements: list[_Requirement],
    fiber: Mapping[tuple[str, str], float],
    order: list[tuple[str, str]],
) -> float:
    return _tighten(_search_over(fiber, order), requirements).miles


def select_fiber(inputs: FiberInputs) -> FiberSelection:
    fiber = {
        key: segment.distance_miles for key, segment in inputs.fiber_segments.items()
    }
    if not fiber:
        return FiberSelection(frozenset(), 0.0)
    requirements = _answered_by_every_wan(_writing(inputs, fiber))
    order = sorted(fiber)
    search = _search_over(fiber, order)
    while True:
        shortfalls = _shortfalls(requirements, _held(fiber, search.selected))
        if not shortfalls:
            break
        _write(search, _rows(shortfalls, search.column))
        search.selected |= _round_up(search, _tighten(search, requirements))
    return FiberSelection(search.selected, _floor_under(requirements, fiber, order))
