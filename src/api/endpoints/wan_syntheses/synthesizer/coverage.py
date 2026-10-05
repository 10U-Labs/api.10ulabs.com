from __future__ import annotations

import logging
from typing import TypedDict

from synthesizer.input_graph import Site, haversine_miles
from synthesizer.model import Synthesis, SynthesisInputs, SynthesisParams
from synthesizer.assemble import build_synthesis_for_wan_pops, evaluate_wan_pops
from synthesizer.ceiling import CircuitProofInputs, diverse_circuit_ceiling
from synthesizer.search_plan import _SearchPlan

logger = logging.getLogger(__name__)


class CoverageReport(TypedDict):
    target_miles: float
    worst_haul_miles: float
    sites_above_target: int
    provider_regions_above_target: int
    met: bool


def hauls(
    wan_pop_ids: tuple[str, ...],
    homed: list[Site],
    pop_by_id: dict[str, Site],
) -> list[float]:
    wan_pops = [pop_by_id[wan_pop_id] for wan_pop_id in wan_pop_ids]
    return [
        min(haversine_miles(member, wan_pop) for wan_pop in wan_pops)
        for member in homed
    ]


def _covered_hauls(
    wan_pop_ids: tuple[str, ...],
    homed: list[Site],
    pop_by_id: dict[str, Site],
) -> list[float]:
    covered = [member for member in homed if not member.exempt_from_distance_constraint]
    return hauls(wan_pop_ids, covered, pop_by_id)


def coverage_haul_profile(
    wan_pop_ids: tuple[str, ...],
    sites: list[Site],
    provider_regions: list[Site],
    pop_by_id: dict[str, Site],
) -> tuple[float, ...]:
    return tuple(sorted(
        _covered_hauls(wan_pop_ids, sites, pop_by_id)
        + _covered_hauls(wan_pop_ids, provider_regions, pop_by_id),
        reverse=True,
    ))


def coverage_worst_haul(profile: tuple[float, ...]) -> float:
    return max(profile, default=0.0)


def _above_target(hauls_measured: list[float], target_miles: float) -> int:
    return sum(1 for haul in hauls_measured if haul > target_miles)


def coverage_report(
    wan_pop_ids: tuple[str, ...],
    sites: list[Site],
    provider_regions: list[Site],
    pop_by_id: dict[str, Site],
    target_miles: float,
) -> CoverageReport:
    worst = coverage_worst_haul(
        coverage_haul_profile(wan_pop_ids, sites, provider_regions, pop_by_id)
    )
    return {
        "target_miles": target_miles,
        "worst_haul_miles": round(worst, 1),
        "sites_above_target": _above_target(
            _covered_hauls(wan_pop_ids, sites, pop_by_id), target_miles
        ),
        "provider_regions_above_target": _above_target(
            _covered_hauls(wan_pop_ids, provider_regions, pop_by_id), target_miles
        ),
        "met": worst <= target_miles,
    }


def coverage_candidate_hauls(
    wan_pop_ids: tuple[str, ...],
    free: list[str],
    inputs: SynthesisInputs,
    plan: _SearchPlan,
    pop_by_id: dict[str, Site],
) -> list[tuple[tuple[float, ...], str]]:
    scored: list[tuple[tuple[float, ...], str]] = []
    for candidate_id in free:
        candidate_set = tuple(sorted((*wan_pop_ids, candidate_id)))
        if evaluate_wan_pops(candidate_set, inputs, plan) is None:
            continue
        profile = coverage_haul_profile(
            candidate_set, inputs.sites, inputs.provider_regions, pop_by_id
        )
        scored.append((profile, candidate_id))
    return scored


def candidate_mesh_ceiling(
    candidate_id: str,
    wan_pop_ids: tuple[str, ...],
    adjacency: dict[str, list[tuple[str, float]]],
) -> int:
    return diverse_circuit_ceiling(
        candidate_id,
        CircuitProofInputs(tuple(sorted((*wan_pop_ids, candidate_id))), adjacency),
    )


def best_coverage_candidate(
    improving: list[tuple[tuple[float, ...], str]],
    wan_pop_ids: tuple[str, ...],
    adjacency: dict[str, list[tuple[str, float]]],
    target_miles: float,
) -> str:
    satisfying = [
        pair for pair in improving if coverage_worst_haul(pair[0]) <= target_miles
    ]
    if not satisfying:
        return min(improving)[1]
    return min(
        satisfying,
        key=lambda pair: (
            -candidate_mesh_ceiling(pair[1], wan_pop_ids, adjacency),
            pair[0],
            pair[1],
        ),
    )[1]


def grow_wan_pops_for_coverage(
    base_ids: tuple[str, ...],
    inputs: SynthesisInputs,
    plan: _SearchPlan,
    params: SynthesisParams,
    pop_by_id: dict[str, Site],
) -> Synthesis:
    target_miles = params.tuning.backbone_coverage_target_miles
    wan_pop_ids = base_ids
    free = [pop_id for pop_id in plan.wan_pop_candidates if pop_id not in wan_pop_ids]
    logger.info(
        "Growing backbone for coverage: %d candidates, %.0f mi target", len(free), target_miles
    )
    while free:
        if params.max_wan_pop_count is not None and len(wan_pop_ids) >= params.max_wan_pop_count:
            logger.info("Coverage growth stopped at the %d-PoP cap", len(wan_pop_ids))
            break
        profile = coverage_haul_profile(
            wan_pop_ids, inputs.sites, inputs.provider_regions, pop_by_id
        )
        worst = coverage_worst_haul(profile)
        if worst <= target_miles:
            logger.info("Coverage met at %d WAN PoPs (worst haul %.0f mi)", len(wan_pop_ids), worst)
            break
        logger.info(
            "Coverage round at %d WAN PoPs: worst haul %.0f mi > %.0f target; "
            "scoring %d candidates",
            len(wan_pop_ids), worst, target_miles, len(free),
        )
        candidates = coverage_candidate_hauls(wan_pop_ids, free, inputs, plan, pop_by_id)
        improving = [pair for pair in candidates if pair[0] < profile]
        if not improving:
            logger.info("No candidate improves coverage; holding at %d WAN PoPs", len(wan_pop_ids))
            break
        best_id = best_coverage_candidate(
            improving,
            wan_pop_ids,
            inputs.adjacency,
            target_miles,
        )
        wan_pop_ids = tuple(sorted((*wan_pop_ids, best_id)))
        free.remove(best_id)
        logger.info(
            "Selected WAN PoP %s for coverage; now %d of them", best_id, len(wan_pop_ids)
        )
    grown = build_synthesis_for_wan_pops(wan_pop_ids, inputs, plan)
    assert grown is not None
    return grown
