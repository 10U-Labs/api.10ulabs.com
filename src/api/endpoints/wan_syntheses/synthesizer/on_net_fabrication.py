from __future__ import annotations

import logging
from dataclasses import dataclass

from synthesizer.local_fiber import (
    LOCAL_FIBER_MIN_HOMING_DEGREE,
    LocalFiberTwinSettings,
    build_local_fiber_twin,
    unique_twin_id,
)
from synthesizer.model import is_carrier_pop
from synthesizer.input_graph import FiberSegment, Vertex

logger = logging.getLogger(__name__)

ON_NET_ID_PREFIX = "fac_"
ON_NET_SEGMENT_NOTE = "synthetic on-net fabrication backbone link"


@dataclass(frozen=True)
class FabricatedOnNetPops:
    vertices: list[Vertex]
    fiber_segments: dict[tuple[str, str], FiberSegment]
    on_net_ids: frozenset[str]


def _coord_key(vertex: Vertex) -> tuple[float, float]:
    return (round(vertex.lat, 4), round(vertex.lon, 4))


def fabricate_missing_on_net_pops(
    vertices: list[Vertex],
    fiber_segments: dict[tuple[str, str], FiberSegment],
    forced_wan_pop_names: frozenset[str] = frozenset(),
) -> FabricatedOnNetPops:
    carrier_pops = [vertex for vertex in vertices if is_carrier_pop(vertex)]
    used_ids = {vertex.id for vertex in vertices}
    augmented_vertices = list(vertices)
    augmented_fiber_segments = dict(fiber_segments)
    on_net_ids: set[str] = set()
    seen_coords: set[tuple[float, float]] = set()
    for forced in sorted(
        (
            vertex for vertex in vertices
            if not is_carrier_pop(vertex) and vertex.name in forced_wan_pop_names
        ),
        key=lambda vertex: vertex.id,
    ):
        coord_key = _coord_key(forced)
        if coord_key in seen_coords:
            continue
        seen_coords.add(coord_key)
        twin_id = unique_twin_id(f"{ON_NET_ID_PREFIX}{forced.id}", used_ids)
        built = build_local_fiber_twin(
            forced, twin_id, carrier_pops,
            LocalFiberTwinSettings(note=ON_NET_SEGMENT_NOTE, max_radius=None),
        )
        if built is None:
            logger.info(
                "Vertex %s has fewer than %d carrier PoPs to wire to; "
                "leaving it demand-only",
                forced.id,
                LOCAL_FIBER_MIN_HOMING_DEGREE,
            )
            continue
        used_ids.add(twin_id)
        augmented_vertices.append(built[0])
        augmented_fiber_segments.update(built[1])
        on_net_ids.add(twin_id)
    return FabricatedOnNetPops(augmented_vertices, augmented_fiber_segments, frozenset(on_net_ids))
