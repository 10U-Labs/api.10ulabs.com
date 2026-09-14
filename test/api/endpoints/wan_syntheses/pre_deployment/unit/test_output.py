from __future__ import annotations

from typing import Any

import fixtures
import pytest
from synthesizer import output
from synthesizer.input_graph import FiberSegment, Site, segment_key
from synthesizer.model import (
    HomingCircuit,
    Homings,
    Synthesis,
    SynthesisArtifacts,
    SynthesisMetrics,
)
from synthesizer.output import synthesis_payload, sorted_fiber_segments

ARTIFACTS = fixtures.ring_artifacts()

_TENANT_HOMING = HomingCircuit("s", "b", 1.0)
_PROVIDER_HOMING = HomingCircuit("r", "b", 1.0)


def _synthesis(homings: Homings) -> Synthesis:
    return Synthesis(
        wan_pop_ids=(),
        transit_ids=(),
        homings=homings,
        fiber_segment_keys=set(),
        drawn_circuits=[],
        metrics=SynthesisMetrics(0.0, 0.0, 0.0),
    )


def _payload_for(
    synthesis: Synthesis, sites: list[Site], fabricated_ids: frozenset[str] = frozenset()
) -> dict[str, Any]:
    fiber = {segment_key("b", "x"): FiberSegment("b", "x", 1.0)}
    artifacts = SynthesisArtifacts(
        [*sites, fixtures.carrier_pop("b")],
        fiber,
        synthesis,
        ARTIFACTS.validation,
        fabricated_ids,
    )
    return synthesis_payload(artifacts)


def test_synthesis_payload_includes_sites() -> None:
    assert "sites" in synthesis_payload(ARTIFACTS)


def test_the_payload_holds_only_the_collections_a_route_serves() -> None:
    assert set(synthesis_payload(ARTIFACTS)) == {
        "sites", "homing_circuits", "fiber_segments", "drawn_circuits"
    }


def test_the_sites_the_wan_includes_are_read_once_for_every_site_published(
        monkeypatch: pytest.MonkeyPatch) -> None:
    read: list[Synthesis] = []

    def _reading(synthesis: Synthesis) -> set[str]:
        read.append(synthesis)
        return set()

    monkeypatch.setattr(output, "included_site_ids", _reading)
    synthesis_payload(ARTIFACTS)
    assert len(read) == 1


def test_synthesis_payload_entries_carry_municipality_and_state() -> None:
    sites = synthesis_payload(ARTIFACTS)["sites"]
    assert all(
        "municipality" in site["info"] and "state" in site["info"] for site in sites
    )


def test_sorted_fiber_segments_is_sorted() -> None:
    keys = sorted_fiber_segments(ARTIFACTS.synthesis)
    assert keys == sorted(keys)


def test_a_tenant_homing_circuit_is_labelled_tenant_to_backbone() -> None:
    payload = _payload_for(
        _synthesis(Homings([_TENANT_HOMING], [])), [fixtures.tenant_site("s")]
    )
    assert payload["homing_circuits"][0]["homing_kind"] == "tenant_to_backbone"


def test_a_provider_homing_circuit_is_labelled_provider_to_backbone() -> None:
    payload = _payload_for(
        _synthesis(Homings([], [_PROVIDER_HOMING])), [fixtures.provider_region("r")]
    )
    assert payload["homing_circuits"][0]["homing_kind"] == "provider_to_backbone"


def _published_sites_with_a_twin() -> dict[str, dict[str, Any]]:
    payload = _payload_for(
        _synthesis(Homings([], [])),
        [fixtures.carrier_pop("fac_s")],
        frozenset({"fac_s"}),
    )
    return {site["id"]: site for site in payload["sites"]}


def test_a_site_the_synthesizer_fabricated_says_so() -> None:
    assert _published_sites_with_a_twin()["fac_s"]["fabricated"] is True


def test_a_carrier_pop_says_it_was_not_fabricated() -> None:
    assert _published_sites_with_a_twin()["b"]["fabricated"] is False


def test_every_published_site_says_whether_it_was_fabricated() -> None:
    assert all("fabricated" in site for site in synthesis_payload(ARTIFACTS)["sites"])
