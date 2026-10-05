from __future__ import annotations

from dataclasses import asdict
from typing import Any

from synthesizer.collections import vertex_role
from synthesizer.input_graph import segment_key
from synthesizer.model import (
    HomingCircuit,
    PROVIDER_HOMING,
    TENANT_HOMING,
    Synthesis,
    SynthesisArtifacts,
)
from synthesizer.validation import included_vertex_ids


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
    vertices = artifacts.vertices
    fiber_segments = artifacts.fiber_segments
    synthesis = artifacts.synthesis
    vertices_by_id = {vertex.id: vertex for vertex in vertices}
    included = included_vertex_ids(synthesis)
    return {
        "vertices": [
            {
                **asdict(vertex),
                "tier_role": vertex_role(vertex, synthesis),
                "included": vertex.id in included,
                "fabricated": vertex.id in artifacts.fabricated_ids,
            }
            for vertex in vertices
        ],
        "homing_circuits": [
            {
                "source_id": homing_circuit.source,
                "source_name": vertices_by_id[homing_circuit.source].name,
                "target_id": homing_circuit.target,
                "target_name": vertices_by_id[homing_circuit.target].name,
                "homing_kind": homing_kind,
                "distance_miles": round(homing_circuit.distance_miles, 3),
            }
            for homing_circuit, homing_kind in _kinded(synthesis)
        ],
        "fiber_segments": [
            {
                "source_id": left,
                "source_name": vertices_by_id[left].name,
                "target_id": right,
                "target_name": vertices_by_id[right].name,
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
                "source_name": vertices_by_id[drawn_circuit.source].name,
                "target_id": drawn_circuit.target,
                "target_name": vertices_by_id[drawn_circuit.target].name,
                "distance_miles": round(drawn_circuit.distance_miles, 3),
                "route": [vertices_by_id[pop_id].name for pop_id in drawn_circuit.pop_ids],
                "reason": drawn_circuit.reason,
                "requested_by": [
                    vertices_by_id[wan_pop_id].name for wan_pop_id in drawn_circuit.requested_by
                ],
            }
            for drawn_circuit in synthesis.drawn_circuits
        ],
    }
