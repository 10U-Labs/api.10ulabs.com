from __future__ import annotations

import pytest

import fixtures
from synthesizer.offnet import RealizedOffNetPops, realize_off_net_pops
from synthesizer.model import is_carrier_pop
from synthesizer.input_graph import Site

def _realize(
    *sites: Site,
    forced: frozenset[str] = frozenset(),
) -> RealizedOffNetPops:
    return realize_off_net_pops(fixtures.carrier_pops_in_a_column(), {}, list(sites), forced)


def test_realize_gives_a_forced_pop_a_twin() -> None:
    result = _realize(fixtures.off_net_pop("dulles", 0.0, 0.5), forced=frozenset({"dulles"}))
    assert len(result.off_net_ids) == 1


def test_the_realized_twin_id_carries_the_off_net_prefix() -> None:
    result = _realize(fixtures.off_net_pop("dulles", 0.0, 0.5), forced=frozenset({"dulles"}))
    assert next(iter(result.off_net_ids)).startswith("offnet_")


def test_realize_adds_local_fiber_segments() -> None:
    result = _realize(fixtures.off_net_pop("dulles", 0.0, 0.5), forced=frozenset({"dulles"}))
    assert len(result.fiber_segments) == 3


def test_the_realized_twin_is_a_carrier_pop() -> None:
    result = _realize(fixtures.off_net_pop("dulles", 0.0, 0.5), forced=frozenset({"dulles"}))
    off_net_id = next(iter(result.off_net_ids))
    assert is_carrier_pop(next(v for v in result.sites if v.id == off_net_id)) is True


def test_realize_ignores_unforced_pops() -> None:
    result = _realize(fixtures.off_net_pop("dulles", 0.0, 0.5))
    assert result.off_net_ids == frozenset()


def test_an_isolated_forced_pop_is_refused_as_the_pop_it_is() -> None:
    with pytest.raises(ValueError, match="^off-net PoP remote has fewer than"):
        _realize(fixtures.off_net_pop("remote", 0.0, 10.0), forced=frozenset({"remote"}))


def test_a_forced_pop_that_is_already_a_carrier_pop_is_rejected() -> None:
    with pytest.raises(ValueError, match="^forced off-net PoP is already a carrier PoP: P0"):
        _realize(fixtures.off_net_pop("P0", 0.0, 0.5), forced=frozenset({"P0"}))
