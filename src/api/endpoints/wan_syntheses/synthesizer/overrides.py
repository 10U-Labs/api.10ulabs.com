from __future__ import annotations

from collections.abc import Set as AbstractSet

from synthesizer.input_graph import FiberSegment, Site, segment_key
from synthesizer.model import (
    SynthesisParams,
    ForcedCircuits,
    NamedCircuit,
    OperatorCircuits,
    RoleOverrides,
    is_carrier_pop,
)


def pop_id_by_name(carrier_pops: list[Site]) -> dict[str, str]:
    return {pop.name: pop.id for pop in carrier_pops}

def resolve_pinned_ids(
    names: tuple[str, ...], name_to_id: dict[str, str], label: str
) -> set[str]:
    resolved: set[str] = set()
    for name in names:
        if name not in name_to_id:
            raise ValueError(f"{label} entry not found in the Carrier graph: {name}")
        resolved.add(name_to_id[name])
    return resolved

def reject_override_conflicts(
    forced_wan_pops: set[str],
    prohibited_wan_pops: AbstractSet[str] = frozenset(),
) -> None:
    clash = forced_wan_pops & prohibited_wan_pops
    if clash:
        raise ValueError(
            "PoPs cannot be both forced onto and prohibited from the backbone tier: "
            f"{sorted(clash)}"
        )


def _resolve_operator_pins(
    sites: list[Site],
    params: SynthesisParams,
) -> tuple[set[str], set[str], set[str]]:
    carrier_pops = [site for site in sites if is_carrier_pop(site)]
    name_to_id = pop_id_by_name(carrier_pops)
    forced_wan_pops = resolve_pinned_ids(
        params.forced_wan_pop_names, name_to_id, "forced_wan_pops"
    )
    prohibited_wan_pops = resolve_pinned_ids(
        params.exclusions.prohibited_wan_pop_names, name_to_id, "prohibited_wan_pops"
    )
    degree_exempt = resolve_pinned_ids(
        params.degree_exempt_wan_pop_names, name_to_id, "degree_exempt_wan_pops"
    )
    reject_override_conflicts(forced_wan_pops, prohibited_wan_pops)
    return forced_wan_pops, prohibited_wan_pops, degree_exempt


def _forced_wan_pop_endpoint(
    name: str, name_to_id: dict[str, str], forced_wan_pops: set[str], label: str
) -> str:
    if name not in name_to_id:
        raise ValueError(f"{label} WAN PoP not found in the Carrier graph: {name}")
    wan_pop_id = name_to_id[name]
    if wan_pop_id not in forced_wan_pops:
        raise ValueError(f"{label} endpoint must be a forced WAN PoP: {name}")
    return wan_pop_id


def _wan_pop_pair(
    circuit: NamedCircuit, name_to_id: dict[str, str], forced_wan_pops: set[str]
) -> tuple[str, str]:
    left = _forced_wan_pop_endpoint(circuit.source, name_to_id, forced_wan_pops, "forced-circuit")
    right = _forced_wan_pop_endpoint(circuit.target, name_to_id, forced_wan_pops, "forced-circuit")
    return segment_key(left, right)


def _forced_home_pair(
    home: NamedCircuit,
    site_id_by_name: dict[str, str],
    name_to_id: dict[str, str],
    forced_wan_pops: set[str],
) -> tuple[str, str]:
    if home.source not in site_id_by_name:
        raise ValueError(f"forced-home site not found: {home.source}")
    wan_pop = _forced_wan_pop_endpoint(home.target, name_to_id, forced_wan_pops, "forced-home")
    return site_id_by_name[home.source], wan_pop


def _excluded_wan_pop_endpoint(name: str, name_to_id: dict[str, str]) -> str:
    if name not in name_to_id:
        raise ValueError(f"prohibited-circuit WAN PoP not found in the Carrier graph: {name}")
    return name_to_id[name]


def _removed_backbone_pair(circuit: NamedCircuit, name_to_id: dict[str, str]) -> tuple[str, str]:
    left = _excluded_wan_pop_endpoint(circuit.source, name_to_id)
    right = _excluded_wan_pop_endpoint(circuit.target, name_to_id)
    return segment_key(left, right)


def _removed_backbone_circuits(
    circuits: tuple[NamedCircuit, ...],
    name_to_id: dict[str, str],
) -> frozenset[tuple[str, str]]:
    return frozenset(_removed_backbone_pair(circuit, name_to_id) for circuit in circuits)


def resolve_forced_circuits(
    circuits: OperatorCircuits,
    sites: list[Site],
    forced_wan_pops: set[str],
) -> ForcedCircuits:
    name_to_id = pop_id_by_name([site for site in sites if is_carrier_pop(site)])
    site_id_by_name = {
        site.name: site.id for site in sites if not is_carrier_pop(site)
    }
    return ForcedCircuits(
        backbone=frozenset(
            _wan_pop_pair(circuit, name_to_id, forced_wan_pops)
            for circuit in circuits.backbone
        ),
        homes=frozenset(
            _forced_home_pair(home, site_id_by_name, name_to_id, forced_wan_pops)
            for home in circuits.homes
        ),
        removed_backbone=_removed_backbone_circuits(circuits.removed_backbone, name_to_id),
    )


def apply_role_overrides(
    sites: list[Site],
    fiber_segments: dict[tuple[str, str], FiberSegment],
    params: SynthesisParams,
    circuits: OperatorCircuits = OperatorCircuits(),
) -> tuple[list[Site], dict[tuple[str, str], FiberSegment], RoleOverrides]:
    forced_wan_pops, prohibited_wan_pops, degree_exempt = _resolve_operator_pins(
        sites, params
    )
    overrides = RoleOverrides(
        forced_wan_pop_ids=frozenset(forced_wan_pops),
        prohibited_wan_pop_ids=frozenset(prohibited_wan_pops),
        degree_exempt_wan_pop_ids=frozenset(degree_exempt),
        forced_circuits=resolve_forced_circuits(circuits, sites, forced_wan_pops),
    )
    return sites, fiber_segments, overrides
