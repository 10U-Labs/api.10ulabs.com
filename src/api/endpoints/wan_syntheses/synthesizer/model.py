from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TypedDict

from synthesizer.input_graph import FiberSegment, Site


@dataclass(frozen=True)
class HomingCircuit:
    source: str
    target: str
    distance_miles: float

TENANT_HOMING = "tenant_to_backbone"
PROVIDER_HOMING = "provider_to_backbone"


@dataclass(frozen=True)
class Homings:
    tenant: list[HomingCircuit]
    provider: list[HomingCircuit]

    def joined(self) -> list[HomingCircuit]:
        return self.tenant + self.provider


@dataclass(frozen=True)
class HomingSites:
    tenant: list[Site]
    provider: list[Site]

    def joined(self) -> list[Site]:
        return self.tenant + self.provider

CIRCUIT_FOR_TARGET = "site_target"
CIRCUIT_FOR_PIN = "operator_pin"
CIRCUIT_FOR_RELIEF = "pop_loss_relief"


@dataclass(frozen=True)
class SynthesisCircuit:
    purpose: str
    source: str
    target: str
    pop_ids: tuple[str, ...]
    distance_miles: float
    reason: str = CIRCUIT_FOR_TARGET
    requested_by: tuple[str, ...] = ()

@dataclass
class SynthesisMetrics:
    tenant_homing_miles: float
    provider_homing_miles: float
    physical_miles: float
    backbone_lower_bound_miles: float = 0.0

@dataclass
class Synthesis:
    wan_pop_ids: tuple[str, ...]
    transit_ids: tuple[str, ...]
    homings: Homings
    fiber_segment_keys: set[tuple[str, str]]
    drawn_circuits: list[SynthesisCircuit]
    metrics: SynthesisMetrics

@dataclass(frozen=True)
class SearchMemoryBudget:
    memory_share: float = 0.6
    bytes_per_combination: int = 160


@dataclass(frozen=True)
class Tuning:
    compass_sector_count: int = 8
    backbone_number_of_diverse_circuits: int = 3
    backbone_coverage_target_miles: int = 600
    homing_degree: int = 2
    search_memory_budget: SearchMemoryBudget = field(default_factory=SearchMemoryBudget)

@dataclass(frozen=True)
class NamedCircuit:
    source: str
    target: str

@dataclass(frozen=True)
class RoleExclusions:
    prohibited_wan_pop_names: tuple[str, ...] = ()

@dataclass(frozen=True)
class SynthesisParams:
    min_wan_pop_count: int = 3
    max_wan_pop_count: int | None = None
    forced_wan_pop_names: tuple[str, ...] = ()
    degree_exempt_wan_pop_names: tuple[str, ...] = ()
    exclusions: RoleExclusions = field(default_factory=RoleExclusions)
    promote_high_degree_convergences: bool = True
    tuning: Tuning = field(default_factory=Tuning)

@dataclass(frozen=True)
class OperatorCircuits:
    backbone: tuple[NamedCircuit, ...] = ()
    homes: tuple[NamedCircuit, ...] = ()
    removed_backbone: tuple[NamedCircuit, ...] = ()

@dataclass(frozen=True)
class ForcedCircuits:
    backbone: frozenset[tuple[str, str]] = frozenset()
    homes: frozenset[tuple[str, str]] = frozenset()
    removed_backbone: frozenset[tuple[str, str]] = frozenset()
    required_wan_pops: frozenset[str] = frozenset()

@dataclass(frozen=True)
class RoleOverrides:
    forced_wan_pop_ids: frozenset[str] = frozenset()
    prohibited_wan_pop_ids: frozenset[str] = frozenset()
    degree_exempt_wan_pop_ids: frozenset[str] = frozenset()
    forced_circuits: ForcedCircuits = field(default_factory=ForcedCircuits)

@dataclass(frozen=True)
class SynthesisInputs:
    homing_sites: HomingSites
    carrier_pops: list[Site]
    fiber_segments: dict[tuple[str, str], FiberSegment]
    eligible_wan_pop_ids: set[str]
    adjacency: dict[str, list[tuple[str, float]]]
    all_distances: dict[str, dict[str, float]]
    all_predecessors: dict[str, dict[str, str]]
    carrier_blocks: dict[str, frozenset[int]]

@dataclass(frozen=True)
class MeshRequirements:
    number_of_diverse_circuits: int = 3
    degree_exempt: frozenset[str] = frozenset()
    ceilings: Mapping[str, int] | None = None


class ValidationReport(TypedDict):
    connected: bool
    component_count: int
    min_distinct_neighbor_degree: int
    degree_deficient_sites: list[dict[str, object]]
    biconnected_no_articulation_points: bool
    articulation_points: list[dict[str, str]]
    every_site_meets_homing_degree: bool
    sites_below_homing_degree: list[dict[str, str]]
    backbone_meets_mesh_link_target: bool
    backbone_diverse_circuits_deficient: list[dict[str, object]]
    backbone_meets_independent_mesh_link_target: bool
    backbone_mesh_independence_deficient: list[dict[str, object]]
    backbone_degree_exempt: list[dict[str, str]]
    backbone_diverse_circuits_ceilings: list[dict[str, object]]
    backbone_diverse_circuits_ceiling_limited: list[dict[str, object]]
    backbone_diverse_circuits_above_target: list[dict[str, object]]
    backbone_mesh_survives_any_one_link_loss: bool
    backbone_mesh_survives_any_one_site_loss: bool
    backbone_mesh_is_one_piece: bool
    backbone_mesh_pieces: list[list[dict[str, str]]]
    backbone_mesh_has_no_cut_pop: bool
    backbone_mesh_cut_pops: list[dict[str, str]]

@dataclass(frozen=True)
class SynthesisArtifacts:
    sites: list[Site]
    fiber_segments: dict[tuple[str, str], FiberSegment]
    synthesis: Synthesis
    validation: ValidationReport
    fabricated_ids: frozenset[str]

KIND_POP = "PoP"
KIND_ROADM = "ROADM"
CARRIER_KINDS = frozenset({KIND_POP, KIND_ROADM})

def is_carrier_pop(site: Site) -> bool:
    return site.kind in CARRIER_KINDS
