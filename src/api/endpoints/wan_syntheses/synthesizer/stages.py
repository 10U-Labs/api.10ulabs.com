from __future__ import annotations

from dataclasses import dataclass

from synthesizer.ceiling import CircuitProofInputs, diverse_circuit_ceilings
from synthesizer.graphs import build_adjacency
from synthesizer.input_graph import FiberSegment, Site
from synthesizer.model import Synthesis, SynthesisParams, MeshRequirements, ValidationReport
from synthesizer.on_net_fabrication import fabricate_missing_on_net_pops
from synthesizer.offnet import realize_off_net_pops
from synthesizer.validation import wan_pop_mesh_target, validate_synthesis


@dataclass(frozen=True)
class DualHomed:
    sites: list[Site]
    fiber_segments: dict[tuple[str, str], FiberSegment]
    fabricated_ids: frozenset[str]


def dual_home(
    sites: list[Site],
    fiber_segments: dict[tuple[str, str], FiberSegment],
    params: SynthesisParams,
    off_net_pops: list[Site],
) -> DualHomed:
    forced_wan_pops = frozenset(params.forced_wan_pop_names)
    fabricated = fabricate_missing_on_net_pops(
        sites, fiber_segments, forced_wan_pops - {site.name for site in off_net_pops}
    )
    off_net = realize_off_net_pops(
        fabricated.sites,
        fabricated.fiber_segments,
        off_net_pops,
        forced_wan_pops,
    )
    return DualHomed(
        off_net.sites,
        off_net.fiber_segments,
        fabricated.on_net_ids | off_net.off_net_ids,
    )


def finalize(
    sites: list[Site],
    fiber_segments: dict[tuple[str, str], FiberSegment],
    synthesis: Synthesis,
    params: SynthesisParams,
    degree_exempt: frozenset[str] = frozenset(),
) -> tuple[
    list[Site], dict[tuple[str, str], FiberSegment], Synthesis, ValidationReport
]:
    adjacency = build_adjacency(fiber_segments)
    terrestrial = build_adjacency({
        key: segment for key, segment in fiber_segments.items() if not segment.submarine
    })
    targets = MeshRequirements(
        number_of_diverse_circuits=params.tuning.backbone_number_of_diverse_circuits,
        degree_exempt=degree_exempt,
        ceilings=diverse_circuit_ceilings(CircuitProofInputs(
            synthesis.wan_pop_ids, adjacency, terrestrial
        )),
    )
    validation = validate_synthesis(
        sites, synthesis, params.tuning.homing_degree, targets
    )
    pieces = validation["backbone_mesh_pieces"]
    if len(pieces) > 1:
        named = "; ".join(", ".join(entry["name"] for entry in piece) for piece in pieces)
        raise ValueError(
            f"The WAN falls into {len(pieces)} pieces no circuit joins: {named}"
        )
    cut_pops = validation["backbone_mesh_cut_pops"]
    if cut_pops:
        splits = ", ".join(str(entry["name"]) for entry in cut_pops)
        raise ValueError(f"Loss of one PoP splits the WAN at: {splits}")
    deficient = validation["backbone_mesh_independence_deficient"]
    if deficient:
        shortfalls = ", ".join(
            f"{entry['name']} ({entry['independent_degree']} of "
            f"{wan_pop_mesh_target(str(entry['id']), targets)})"
            for entry in deficient
        )
        raise ValueError(
            f"Too few independently failing backbone mesh circuits at: {shortfalls}"
        )
    return sites, fiber_segments, synthesis, validation
