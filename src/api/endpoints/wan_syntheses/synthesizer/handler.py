from __future__ import annotations

import logging
import os
from typing import Any, NamedTuple

from store import assign, member, members, partition, plain, put, sort_id, typed
from synthesizer import collections as published
from synthesizer.codec import load_merged_carriers, load_off_net, load_regions, load_sites
from synthesizer.config import LIST_INPUTS, AppConfig, app_config_from_record
from synthesizer.coverage import coverage_report
from synthesizer.input_graph import FiberSegment, Site
from synthesizer.model import SynthesisArtifacts, SynthesisParams, is_carrier_pop
from synthesizer.output import synthesis_payload
from synthesizer.overrides import apply_role_overrides
from synthesizer.stages import dual_home, finalize
from synthesizer.synthesize import synthesize_two_tier

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COLLECTION = "wan-syntheses"
CARRIERS = "carriers"
KEY = ("PK", "SK")
NAMED = ("forced_wan_pops", "prohibited_wan_pops", "degree_exempt_wan_pops")
WAN_POPS = "wan-pops"
BACKBONE_CIRCUITS = "backbone-circuits"
HOMING_CIRCUITS = "homing-circuits"
FIBER_SEGMENTS = "fiber-segments"


def _fields(item: dict[str, Any]) -> dict[str, Any]:
    return {field: plain(value) for field, value in item.items() if field not in KEY}


def _rows(table: str, key: str, prefix: str) -> list[dict[str, Any]]:
    items = sorted(partition(table, key, f"{prefix}/"), key=sort_id)
    return [{"id": sort_id(item), **_fields(item)} for item in items]


def _record(table: str, synthesis_id: int) -> dict[str, Any]:
    item = member(table, COLLECTION, str(synthesis_id))
    if item is None:
        raise LookupError(f"No wan synthesis {synthesis_id}")
    return _fields(item)


def _inputs(table: str, synthesis_id: int) -> dict[str, list[dict[str, Any]]]:
    under = f"{COLLECTION}/{synthesis_id}"
    return {
        field: _rows(table, under, field.replace("_", "-"))
        for field in (
            "sites", "hyperscale_cloud_service_provider_regions", "off_net", *LIST_INPUTS
        )
    }


def _lists(inputs: dict[str, list[dict[str, Any]]]) -> dict[str, list[Any]]:
    return {
        field: [
            row["name"] if field in NAMED else {"source": row["source"], "target": row["target"]}
            for row in inputs[field]
        ]
        for field in LIST_INPUTS
    }


def _carrier_rows(table: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pops: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []
    for carrier in sorted(members(table, CARRIERS), key=sort_id):
        name = carrier["name"]["S"]
        under = f"{CARRIERS}/{carrier['SK']['S']}"
        pops += [{**row, "carrier": name} for row in _rows(table, under, "pops")]
        segments += [{**row, "carrier": name} for row in _rows(table, under, "fiber-segments")]
    return pops, segments


def _owners(pops: list[dict[str, Any]]) -> dict[tuple[str, str], str]:
    owners: dict[tuple[str, str], str] = {}
    for row in sorted(pops, key=lambda row: str(row["carrier"])):
        owners.setdefault((row["municipality"], row["state"]), row["carrier"])
    return owners


def _delivered(artifacts: SynthesisArtifacts, params: SynthesisParams) -> dict[str, Any]:
    synthesis = artifacts.synthesis
    coverage = coverage_report(
        synthesis.wan_pop_ids,
        [site for site in artifacts.sites if not is_carrier_pop(site)],
        {site.id: site for site in artifacts.sites},
        params.tuning.backbone_coverage_target_miles,
    )
    logger.info("Coverage delivered: %s", coverage)
    short = artifacts.validation["backbone_mesh_independence_deficient"]
    logger.info("Sites short of their diverse-circuit target: %s", short)
    return {
        "coverage": coverage,
        "fiber_miles": round(synthesis.metrics.physical_miles, 3),
        "backbone_lower_bound_miles": round(synthesis.metrics.backbone_lower_bound_miles, 3),
        "homing_miles": {
            "tenant": round(synthesis.metrics.tenant_homing_miles, 3),
            "provider": round(synthesis.metrics.provider_homing_miles, 3),
        },
        "diverse_circuits": {
            "number_of_diverse_circuits": params.tuning.backbone_number_of_diverse_circuits,
            "ceilings": artifacts.validation["backbone_diverse_circuits_ceilings"],
            "short": short,
        },
    }


def _wan_pops(
    payload: dict[str, Any], owners: dict[tuple[str, str], str]
) -> list[dict[str, Any]]:
    return [
        {
            "name": row["name"],
            **{field: row["info"][field] for field in ("municipality", "state", "country")},
            "latitude": row["coords"][0],
            "longitude": row["coords"][1],
            "carrier": owners.get((row["info"]["municipality"], row["info"]["state"]), ""),
        }
        for row in published.wan_pops(payload)
    ]


def _backbone_circuits(
    payload: dict[str, Any], pop_ids: dict[str, int]
) -> list[dict[str, Any]]:
    return [
        {
            "source": pop_ids[circuit["source_id"]],
            "target": pop_ids[circuit["target_id"]],
            "route": circuit["route"],
            "distance_miles": circuit["distance_miles"],
            "reason": circuit["reason"],
            "requested_by": circuit["requested_by"],
        }
        for circuit in published.backbone_circuits(payload)
    ]


def _homing_circuits(
    payload: dict[str, Any], pop_ids: dict[str, int], given: dict[str, int]
) -> list[dict[str, Any]]:
    return [
        {
            "source_id": given[circuit["source_id"]],
            "homing_kind": circuit["homing_kind"],
            "target": pop_ids[circuit["target_id"]],
            "route": [circuit["source_name"], circuit["target_name"]],
            "distance_miles": circuit["distance_miles"],
        }
        for circuit in published.homing_circuits(payload)
    ]


def _end(site: Site, end: str) -> dict[str, Any]:
    return {
        f"{end}_municipality": site.info.municipality,
        f"{end}_state": site.info.state,
        f"{end}_latitude": site.lat,
        f"{end}_longitude": site.lon,
    }


def _fiber_segments(artifacts: SynthesisArtifacts) -> list[dict[str, Any]]:
    by_id = {site.id: site for site in artifacts.sites}
    rows: list[dict[str, Any]] = []
    for left, right in sorted(artifacts.synthesis.fiber_segment_keys):
        segment = artifacts.fiber_segments[(left, right)]
        rows.append({
            "carrier": min(segment.carriers, default=""),
            **_end(by_id[left], "a"),
            **_end(by_id[right], "z"),
            "distance_miles": round(segment.distance_miles, 3),
            "submarine": segment.submarine,
        })
    return rows


def _published(
    artifacts: SynthesisArtifacts, owners: dict[tuple[str, str], str], given: dict[str, int]
) -> dict[str, list[dict[str, Any]]]:
    payload = synthesis_payload(artifacts)
    pop_ids = {row["id"]: position for position, row in enumerate(published.wan_pops(payload), 1)}
    return {
        WAN_POPS: _wan_pops(payload, owners),
        BACKBONE_CIRCUITS: _backbone_circuits(payload, pop_ids),
        HOMING_CIRCUITS: _homing_circuits(payload, pop_ids, given),
        FIBER_SEGMENTS: _fiber_segments(artifacts),
    }


class Loaded(NamedTuple):
    graph: list[Site]
    fiber_segments: dict[tuple[str, str], FiberSegment]
    off_net: list[Site]
    config: AppConfig
    given: dict[str, int]
    owners: dict[tuple[str, str], str]


def _given(
    inputs: dict[str, list[dict[str, Any]]], sites: list[Site], regions: list[Site]
) -> dict[str, int]:
    rows = inputs["sites"] + inputs["hyperscale_cloud_service_provider_regions"]
    return {site.id: row["id"] for row, site in zip(rows, sites + regions)}


def _load(table: str, synthesis_id: int) -> Loaded:
    record = _record(table, synthesis_id)
    inputs = _inputs(table, synthesis_id)
    logger.info("Loading the carriers and the inputs of synthesis %s", synthesis_id)
    pop_rows, segment_rows = _carrier_rows(table)
    carrier_pops, fiber_segments = load_merged_carriers(pop_rows, segment_rows)
    sites = load_sites(inputs["sites"])
    regions = load_regions(inputs["hyperscale_cloud_service_provider_regions"])
    return Loaded(
        carrier_pops + sites + regions,
        fiber_segments,
        load_off_net(inputs["off_net"]),
        app_config_from_record(record, _lists(inputs)),
        _given(inputs, sites, regions),
        _owners(pop_rows),
    )


def _synthesize(loaded: Loaded) -> SynthesisArtifacts:
    params = loaded.config.params
    logger.info(
        "Dual-homing %d sites over %d fiber segments", len(loaded.graph), len(loaded.fiber_segments)
    )
    homed = dual_home(loaded.graph, loaded.fiber_segments, params, loaded.off_net)
    graph, fiber_segments, overrides = apply_role_overrides(
        homed.sites, homed.fiber_segments, params, loaded.config.operator_circuits
    )
    logger.info("Synthesizing the two-tier WAN (this is the long step)")
    synthesis = synthesize_two_tier(graph, fiber_segments, params, overrides)
    logger.info("Finalizing and validating the synthesis")
    graph, fiber_segments, synthesis, validation = finalize(
        graph, fiber_segments, synthesis, params, overrides.degree_exempt_wan_pop_ids
    )
    return SynthesisArtifacts(graph, fiber_segments, synthesis, validation, homed.fabricated_ids)


def _build_wan(
    table: str, synthesis_id: int
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    loaded = _load(table, synthesis_id)
    artifacts = _synthesize(loaded)
    parts = _published(artifacts, loaded.owners, loaded.given)
    return parts, _delivered(artifacts, loaded.config.params)


def _publish(table: str, synthesis_id: int, parts: dict[str, list[dict[str, Any]]]) -> None:
    under = f"{COLLECTION}/{synthesis_id}"
    for prefix, rows in parts.items():
        for position, row in enumerate(rows, 1):
            put(table, under, f"{prefix}/{position}", {
                field: typed(value) for field, value in row.items()
            })


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    table = os.environ["STORE_TABLE"]
    synthesis_id = int(event["synthesis"])
    assign(table, COLLECTION, str(synthesis_id), {"status": "synthesizing"})
    logger.info("Synthesis %s started", synthesis_id)
    try:
        parts, delivered = _build_wan(table, synthesis_id)
    except ValueError as refusal:
        logger.warning("Synthesis %s failed: %s", synthesis_id, refusal)
        assign(table, COLLECTION, str(synthesis_id), {"status": "fail", "reason": str(refusal)})
        return {"status": "fail", "synthesis": synthesis_id}
    logger.info("Publishing the WAN of synthesis %s", synthesis_id)
    _publish(table, synthesis_id, parts)
    assign(table, COLLECTION, str(synthesis_id), {"status": "success", **delivered})
    logger.info("Synthesis %s succeeded", synthesis_id)
    return {"status": "success", "synthesis": synthesis_id}
