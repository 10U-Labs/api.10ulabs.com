from __future__ import annotations

from typing import Any

import fixtures
from synthesizer import collections as gc
from synthesizer.model import Homings, Synthesis, SynthesisMetrics
from synthesizer.output import synthesis_payload


def _payload() -> dict[str, Any]:
    return synthesis_payload(fixtures.ring_artifacts())


def _synthesis(wan_pop_ids: tuple[str, ...], transit_ids: tuple[str, ...]) -> Synthesis:
    return Synthesis(
        wan_pop_ids, transit_ids, Homings([], []), set(), [],
        SynthesisMetrics(0.0, 0.0, 0.0),
    )


def test_site_role_wan_pop_for_selected_pop() -> None:
    assert gc.site_role(fixtures.carrier_pop("a"), _synthesis(("a",), ())) == "wan_pop"


def test_site_role_transit_for_routing_only_pop() -> None:
    assert gc.site_role(fixtures.carrier_pop("a"), _synthesis((), ("a",))) == "transit"


def test_site_role_unused_for_unselected_pop() -> None:
    assert gc.site_role(fixtures.carrier_pop("a"), _synthesis((), ())) == "unused"


def test_site_role_tenant_for_a_site() -> None:
    assert gc.site_role(fixtures.tenant_site("s"), _synthesis((), ())) == "tenant"


def test_site_role_provider_for_a_provider_region() -> None:
    assert gc.site_role(fixtures.provider_region("r"), _synthesis((), ())) == "provider"


def test_homing_circuits_are_the_payloads_homing_circuits() -> None:
    payload = _payload()
    assert gc.homing_circuits(payload) == payload["homing_circuits"]


def test_fiber_segments_are_the_payloads_fiber_segments() -> None:
    payload = _payload()
    assert gc.fiber_segments(payload) == payload["fiber_segments"]


def test_wan_pops_are_all_tier_wan_pop() -> None:
    assert all(site["tier_role"] == "wan_pop" for site in gc.wan_pops(_payload()))


def test_backbone_circuits_exist_for_a_meshed_synthesis() -> None:
    assert gc.backbone_circuits(_payload())


def test_backbone_circuits_are_all_backbone_mesh_circuits() -> None:
    assert all(
        circuit["purpose"] == "backbone_mesh" for circuit in gc.backbone_circuits(_payload())
    )


def test_backbone_circuits_omit_other_drawn_circuits() -> None:
    assert gc.backbone_circuits({"drawn_circuits": [{"purpose": "access"}]}) == []


def test_backbone_circuits_name_both_endpoints() -> None:
    assert all(
        circuit["source_name"] and circuit["target_name"]
        for circuit in gc.backbone_circuits(_payload())
    )
