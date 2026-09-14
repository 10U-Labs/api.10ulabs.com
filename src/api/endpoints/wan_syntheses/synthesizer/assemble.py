from __future__ import annotations

from dataclasses import dataclass

from synthesizer.input_graph import FiberSegment, Site, haversine_miles
from synthesizer.model import (
    HomingCircuit,
    Homings,
    Synthesis,
    SynthesisInputs,
    SynthesisMetrics,
    SynthesisCircuit,
)
from synthesizer.forced import (
    apply_forced_homes,
    forced_backbone_pairs,
    removed_backbone_pairs,
)
from synthesizer.graphs import fiber_segments_along
from synthesizer.backbone import WanPopConstraints, BackboneMesh, backbone_mesh
from synthesizer.search_plan import _SearchPlan


@dataclass
class _SynthesisDraft:
    homings: Homings
    drawn_circuits: list[SynthesisCircuit]
    backbone_lower_bound_miles: float = 0.0


def finalize_synthesis(
    wan_pop_ids: tuple[str, ...],
    draft: _SynthesisDraft,
    fiber_segments: dict[tuple[str, str], FiberSegment],
) -> Synthesis:
    fiber_segment_keys: set[tuple[str, str]] = set()
    for drawn_circuit in draft.drawn_circuits:
        fiber_segment_keys.update(fiber_segments_along(drawn_circuit.pop_ids))

    tenant_homing_miles = homing_miles(draft.homings.tenant)
    provider_homing_miles = homing_miles(draft.homings.provider)
    physical_miles = sum(
        fiber_segments[key].distance_miles for key in fiber_segment_keys
    )
    carrier_on_circuits = {
        site_id
        for drawn_circuit in draft.drawn_circuits
        for site_id in drawn_circuit.pop_ids
    }
    transit_ids = tuple(sorted(carrier_on_circuits - set(wan_pop_ids)))
    return Synthesis(
        wan_pop_ids=wan_pop_ids,
        transit_ids=transit_ids,
        homings=draft.homings,
        fiber_segment_keys=fiber_segment_keys,
        drawn_circuits=draft.drawn_circuits,
        metrics=SynthesisMetrics(
            tenant_homing_miles,
            provider_homing_miles,
            physical_miles,
            draft.backbone_lower_bound_miles,
        ),
    )


def homing_miles(homing_circuits: list[HomingCircuit]) -> float:
    return sum(homing_circuit.distance_miles for homing_circuit in homing_circuits)


def home_sites(
    sites: list[Site],
    wan_pop_set: set[str],
    plan: _SearchPlan,
    pop_by_id: dict[str, Site],
) -> list[HomingCircuit]:
    homing_degree = plan.tuning.homing_degree
    homing_circuits: list[HomingCircuit] = []
    for site in sites:
        completed = [
            wan_pop_id
            for _distance, wan_pop_id in sorted(
                (haversine_miles(site, pop_by_id[wan_pop_id]), wan_pop_id)
                for wan_pop_id in wan_pop_set
            )
        ][:homing_degree]
        completed = apply_forced_homes(
            site, completed, plan.forced_circuits, pop_by_id, homing_degree
        )
        homing_circuits.extend(
            HomingCircuit(
                site.id, wan_pop_id,
                haversine_miles(site, pop_by_id[wan_pop_id]),
            )
            for wan_pop_id in completed
        )
    return homing_circuits


def assign_homes(
    wan_pop_ids: tuple[str, ...],
    inputs: SynthesisInputs,
    plan: _SearchPlan,
) -> Homings | None:
    wan_pop_set = set(wan_pop_ids)
    if len(wan_pop_set) < plan.tuning.homing_degree:
        return None
    pop_by_id = {pop.id: pop for pop in inputs.carrier_pops}
    return Homings(
        home_sites(inputs.homing_sites.tenant, wan_pop_set, plan, pop_by_id),
        home_sites(inputs.homing_sites.provider, wan_pop_set, plan, pop_by_id),
    )


def wan_pops_physically_biconnectable(
    wan_pop_ids: tuple[str, ...], inputs: SynthesisInputs
) -> bool:
    common: frozenset[int] | None = None
    for site in wan_pop_ids:
        blocks = inputs.carrier_blocks.get(site, frozenset())
        common = blocks if common is None else common & blocks
    return common is not None and bool(common)


def forced_wan_pop_resilience_error(
    required: frozenset[str], inputs: SynthesisInputs, min_count: int
) -> str | None:
    if not required:
        return None
    blocks_by_id = inputs.carrier_blocks
    pop_by_id = {pop.id: pop for pop in inputs.carrier_pops}
    names = ", ".join(sorted(pop_by_id[site].name for site in required))
    common = blocks_by_id.get(next(iter(required)), frozenset())
    for site in required:
        common &= blocks_by_id.get(site, frozenset())
    if not common:
        return (
            "Forced WAN PoPs share no common biconnected block of the carrier fiber "
            f"graph, so no synthesis can survive a single city loss: {names}"
        )
    best = max(
        sum(
            1
            for site in inputs.eligible_wan_pop_ids
            if block in blocks_by_id.get(site, frozenset())
        )
        for block in common
    )
    if best < min_count:
        return (
            "A forced WAN PoP sits in a carrier fiber pocket too small for a "
            f"{min_count}-PoP biconnected backbone: {names}"
        )
    return None


def evaluate_wan_pops(
    wan_pop_ids: tuple[str, ...],
    inputs: SynthesisInputs,
    plan: _SearchPlan,
) -> Homings | None:
    if not wan_pops_physically_biconnectable(wan_pop_ids, inputs):
        return None
    return assign_homes(wan_pop_ids, inputs, plan)


def synthesis_circuits(
    wan_pop_ids: tuple[str, ...],
    inputs: SynthesisInputs,
    plan: _SearchPlan,
    fiber_segments: dict[tuple[str, str], FiberSegment],
) -> BackboneMesh:
    wan_pop_set = set(wan_pop_ids)
    constraints = WanPopConstraints(
        removed_backbone_pairs(wan_pop_set, plan.forced_circuits),
        number_of_diverse_circuits=plan.tuning.backbone_number_of_diverse_circuits,
        forced_pairs=forced_backbone_pairs(wan_pop_set, plan.forced_circuits),
    )
    return backbone_mesh(wan_pop_ids, inputs.all_distances, fiber_segments, constraints)


def build_synthesis_for_wan_pops(
    wan_pop_ids: tuple[str, ...],
    inputs: SynthesisInputs,
    plan: _SearchPlan,
) -> Synthesis | None:
    homings = evaluate_wan_pops(wan_pop_ids, inputs, plan)
    if homings is None:
        return None
    mesh = synthesis_circuits(wan_pop_ids, inputs, plan, inputs.fiber_segments)
    draft = _SynthesisDraft(homings, mesh.circuits, mesh.lower_bound_miles)
    return finalize_synthesis(wan_pop_ids, draft, inputs.fiber_segments)
