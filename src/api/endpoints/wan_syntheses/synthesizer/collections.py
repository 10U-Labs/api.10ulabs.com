from __future__ import annotations

from typing import Any

from synthesizer.codec import PROVIDER_KIND
from synthesizer.input_graph import Site
from synthesizer.model import Synthesis, is_carrier_pop


def site_role(site: Site, synthesis: Synthesis) -> str:
    if not is_carrier_pop(site):
        return "provider" if site.kind == PROVIDER_KIND else "tenant"
    if site.id in synthesis.wan_pop_ids:
        return "wan_pop"
    if site.id in synthesis.transit_ids:
        return "transit"
    return "unused"


def _published(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = payload[key]
    return result


def homing_circuits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return _published(payload, "homing_circuits")


def fiber_segments(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return _published(payload, "fiber_segments")


def backbone_circuits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        drawn_circuit
        for drawn_circuit in payload["drawn_circuits"]
        if drawn_circuit["purpose"] == "backbone_mesh"
    ]


def _tier(payload: dict[str, Any], tier_role: str) -> list[dict[str, Any]]:
    return [site for site in payload["sites"] if site["tier_role"] == tier_role]


def wan_pops(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return _tier(payload, "wan_pop")
