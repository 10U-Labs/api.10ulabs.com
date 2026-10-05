from __future__ import annotations

from dataclasses import dataclass

from synthesizer.local_fiber import (
    LOCAL_FIBER_MIN_HOMING_DEGREE,
    LOCAL_FIBER_RADIUS_MILES,
    LocalFiberTwinSettings,
    build_local_fiber_twin,
    unique_twin_id,
)
from synthesizer.model import is_carrier_pop
from synthesizer.input_graph import FiberSegment, Vertex

OFF_NET_ID_PREFIX = "offnet_"
OFF_NET_SEGMENT_NOTE = "synthetic off-net local-fiber link"


@dataclass(frozen=True)
class RealizedOffNetPops:
    vertices: list[Vertex]
    fiber_segments: dict[tuple[str, str], FiberSegment]
    off_net_ids: frozenset[str]


def realize_off_net_pops(
    vertices: list[Vertex],
    fiber_segments: dict[tuple[str, str], FiberSegment],
    off_net_roster: list[Vertex],
    forced_names: frozenset[str],
) -> RealizedOffNetPops:
    carrier_pops = [vertex for vertex in vertices if is_carrier_pop(vertex)]
    carrier_names = {pop.name for pop in carrier_pops}
    used_ids = {vertex.id for vertex in vertices}
    augmented_vertices = list(vertices)
    augmented_fiber_segments = dict(fiber_segments)
    off_net_ids: set[str] = set()
    for off_net_pop in sorted(off_net_roster, key=lambda off_net_pop: off_net_pop.id):
        if off_net_pop.name not in forced_names:
            continue
        if off_net_pop.name in carrier_names:
            raise ValueError(
                f"forced off-net PoP is already a carrier PoP: {off_net_pop.name}"
            )
        twin_id = unique_twin_id(f"{OFF_NET_ID_PREFIX}{off_net_pop.id}", used_ids)
        built = build_local_fiber_twin(
            off_net_pop, twin_id, carrier_pops,
            LocalFiberTwinSettings(note=OFF_NET_SEGMENT_NOTE),
        )
        if built is None:
            raise ValueError(
                f"off-net PoP {off_net_pop.name} has fewer than {LOCAL_FIBER_MIN_HOMING_DEGREE} "
                f"carrier PoPs within {LOCAL_FIBER_RADIUS_MILES:.0f} mi; "
                "cannot select it as a WAN PoP"
            )
        used_ids.add(twin_id)
        augmented_vertices.append(built[0])
        augmented_fiber_segments.update(built[1])
        off_net_ids.add(twin_id)
    return RealizedOffNetPops(augmented_vertices, augmented_fiber_segments, frozenset(off_net_ids))
