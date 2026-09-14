from __future__ import annotations

from dataclasses import asdict
from typing import Any

from synthesizer.collections import site_role
from synthesizer.input_graph import segment_key
from synthesizer.model import (
    HomingCircuit,
    PROVIDER_HOMING,
    TENANT_HOMING,
    Synthesis,
    SynthesisArtifacts,
)
from synthesizer.validation import included_site_ids


def sorted_fiber_segments(synthesis: Synthesis) -> list[tuple[str, str]]:
    return sorted(synthesis.fiber_segment_keys)


def _kinded(synthesis: Synthesis) -> list[tuple[HomingCircuit, str]]:
    return sorted(
        [(homing_circuit, TENANT_HOMING) for homing_circuit in synthesis.homings.tenant]
        + [
            (homing_circuit, PROVIDER_HOMING)
            for homing_circuit in synthesis.homings.provider
        ],
        key=lambda pair: (pair[0].source, pair[0].target),
    )


def synthesis_payload(artifacts: SynthesisArtifacts) -> dict[str, Any]:
    sites = artifacts.sites
    fiber_segments = artifacts.fiber_segments
    synthesis = artifacts.synthesis
    sites_by_id = {site.id: site for site in sites}
    included = included_site_ids(synthesis)
    return {
        "sites": [
            {
                **asdict(site),
                "tier_role": site_role(site, synthesis),
                "included": site.id in included,
                "fabricated": site.id in artifacts.fabricated_ids,
            }
            for site in sites
        ],
        "homing_circuits": [
            {
                "source_id": homing_circuit.source,
                "source_name": sites_by_id[homing_circuit.source].name,
                "target_id": homing_circuit.target,
                "target_name": sites_by_id[homing_circuit.target].name,
                "homing_kind": homing_kind,
                "distance_miles": round(homing_circuit.distance_miles, 3),
            }
            for homing_circuit, homing_kind in _kinded(synthesis)
        ],
        "fiber_segments": [
            {
                "source_id": left,
                "source_name": sites_by_id[left].name,
                "target_id": right,
                "target_name": sites_by_id[right].name,
                "distance_miles": round(fiber_segments[segment_key(left, right)].distance_miles, 3),
                "source_page": fiber_segments[segment_key(left, right)].source_page,
                "note": fiber_segments[segment_key(left, right)].note,
                "submarine": fiber_segments[segment_key(left, right)].submarine,
            }
            for left, right in sorted_fiber_segments(synthesis)
        ],
        "drawn_circuits": [
            {
                "purpose": drawn_circuit.purpose,
                "source_id": drawn_circuit.source,
                "source_name": sites_by_id[drawn_circuit.source].name,
                "target_id": drawn_circuit.target,
                "target_name": sites_by_id[drawn_circuit.target].name,
                "distance_miles": round(drawn_circuit.distance_miles, 3),
                "route": [sites_by_id[site_id].name for site_id in drawn_circuit.pop_ids],
                "reason": drawn_circuit.reason,
                "requested_by": [
                    sites_by_id[site_id].name for site_id in drawn_circuit.requested_by
                ],
            }
            for drawn_circuit in synthesis.drawn_circuits
        ],
    }
