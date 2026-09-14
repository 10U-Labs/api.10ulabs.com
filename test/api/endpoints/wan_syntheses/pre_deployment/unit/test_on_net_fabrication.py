from __future__ import annotations

import pytest

import fixtures
from synthesizer.on_net_fabrication import (
    FabricatedOnNetPops,
    fabricate_missing_on_net_pops,
)
from synthesizer.model import is_carrier_pop
from synthesizer.input_graph import Site

def _fabricate(
    *extra: Site,
    forced: frozenset[str] = frozenset(),
) -> FabricatedOnNetPops:
    sites = [*fixtures.carrier_pops_in_a_column(), *extra]
    return fabricate_missing_on_net_pops(sites, {}, forced)


def test_fabricates_a_forced_twin() -> None:
    result = _fabricate(
        fixtures.tenant_site("luke", 0.0, 0.5), forced=frozenset({"luke"})
    )
    assert result.on_net_ids == frozenset({"fac_luke"})


def test_fabrication_adds_backbone_fiber_segments() -> None:
    result = _fabricate(
        fixtures.tenant_site("luke", 0.0, 0.5), forced=frozenset({"luke"})
    )
    assert len(result.fiber_segments) == 3


def test_fabricated_twin_is_a_carrier_pop() -> None:
    result = _fabricate(
        fixtures.tenant_site("luke", 0.0, 0.5), forced=frozenset({"luke"})
    )
    assert is_carrier_pop(next(v for v in result.sites if v.id == "fac_luke")) is True


def test_ignores_unforced_sites() -> None:
    result = _fabricate(fixtures.tenant_site("luke", 0.0, 0.5))
    assert result.on_net_ids == frozenset()


def test_fabricates_a_forced_remote_site_regardless_of_distance() -> None:
    result = _fabricate(
        fixtures.tenant_site("remote", 0.0, 10.0), forced=frozenset({"remote"})
    )
    assert result.on_net_ids == frozenset({"fac_remote"})


def test_collapses_colocated_sites() -> None:
    result = _fabricate(
        fixtures.tenant_site("hill", 0.0, 0.5),
        fixtures.tenant_site("ogden", 0.0, 0.5),
        forced=frozenset({"hill", "ogden"}),
    )
    assert len(result.on_net_ids) == 1


def test_demand_only_when_too_few_carrier_pops() -> None:
    result = fabricate_missing_on_net_pops(
        [fixtures.carrier_pop("P0", 0.0, 0.0), fixtures.tenant_site("luke", 0.0, 0.5)],
        {},
        frozenset({"luke"}),
    )
    assert result.on_net_ids == frozenset()


def test_avoids_id_collision() -> None:
    result = _fabricate(
        fixtures.carrier_pop("fac_luke", 0.0, 0.5),
        fixtures.tenant_site("luke", 0.0, 0.6),
        forced=frozenset({"luke"}),
    )
    assert "fac_luke_2" in result.on_net_ids


def test_a_forced_site_no_fiber_can_reach_is_left_demand_only_as_a_site(
        caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("INFO"):
        fabricate_missing_on_net_pops(
            [fixtures.tenant_site("alone", 0.0, 0.5)], {}, frozenset({"alone"})
        )
    assert [record.getMessage() for record in caplog.records] == [
        "Site alone has fewer than 2 carrier PoPs to wire to; leaving it demand-only"
    ]
