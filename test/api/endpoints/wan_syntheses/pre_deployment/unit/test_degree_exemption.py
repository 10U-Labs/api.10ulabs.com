from __future__ import annotations

import pytest

import fixtures
from synthesizer.model import SynthesisParams
from synthesizer.overrides import apply_role_overrides

pop = fixtures.carrier_pop
physical = fixtures.fiber_segments_from


def test_apply_role_overrides_resolves_a_degree_exempt_name() -> None:
    params = SynthesisParams(degree_exempt_wan_pop_names=("P0",))
    _sites, _fiber, overrides = apply_role_overrides(
        [pop("P0"), pop("P1")], physical({("P0", "P1"): 1.0}), params
    )
    assert overrides.degree_exempt_wan_pop_ids == frozenset({"P0"})


def test_apply_role_overrides_exempts_nobody_by_default() -> None:
    _sites, _fiber, overrides = apply_role_overrides(
        [pop("P0"), pop("P1")], physical({("P0", "P1"): 1.0}), SynthesisParams()
    )
    assert overrides.degree_exempt_wan_pop_ids == frozenset()


def test_apply_role_overrides_rejects_an_unknown_degree_exempt_name() -> None:
    params = SynthesisParams(degree_exempt_wan_pop_names=("Nowhere",))
    with pytest.raises(ValueError, match="degree_exempt_wan_pops"):
        apply_role_overrides([pop("P0")], physical({("P0", "P1"): 1.0}), params)
