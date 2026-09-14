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
from synthesizer.input_graph import FiberSegment, Site

OFF_NET_ID_PREFIX = "offnet_"
OFF_NET_SEGMENT_NOTE = "synthetic off-net local-fiber link"


@dataclass(frozen=True)
class RealizedOffNetPops:
    sites: list[Site]
    fiber_segments: dict[tuple[str, str], FiberSegment]
    off_net_ids: frozenset[str]


def realize_off_net_pops(
    sites: list[Site],
    fiber_segments: dict[tuple[str, str], FiberSegment],
    off_net_roster: list[Site],
    forced_names: frozenset[str],
) -> RealizedOffNetPops:
    carrier_pops = [site for site in sites if is_carrier_pop(site)]
    carrier_names = {pop.name for pop in carrier_pops}
    used_ids = {site.id for site in sites}
    augmented_sites = list(sites)
    augmented_fiber_segments = dict(fiber_segments)
    off_net_ids: set[str] = set()
    for site in sorted(off_net_roster, key=lambda site: site.id):
        if site.name not in forced_names:
            continue
        if site.name in carrier_names:
            raise ValueError(
                f"forced off-net PoP is already a carrier PoP: {site.name}"
            )
        twin_id = unique_twin_id(f"{OFF_NET_ID_PREFIX}{site.id}", used_ids)
        built = build_local_fiber_twin(
            site, twin_id, carrier_pops,
            LocalFiberTwinSettings(note=OFF_NET_SEGMENT_NOTE),
        )
        if built is None:
            raise ValueError(
                f"off-net PoP {site.name} has fewer than {LOCAL_FIBER_MIN_HOMING_DEGREE} "
                f"carrier PoPs within {LOCAL_FIBER_RADIUS_MILES:.0f} mi; "
                "cannot select it as a WAN PoP"
            )
        used_ids.add(twin_id)
        augmented_sites.append(built[0])
        augmented_fiber_segments.update(built[1])
        off_net_ids.add(twin_id)
    return RealizedOffNetPops(augmented_sites, augmented_fiber_segments, frozenset(off_net_ids))
