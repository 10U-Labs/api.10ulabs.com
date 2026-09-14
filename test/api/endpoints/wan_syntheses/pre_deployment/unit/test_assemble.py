from __future__ import annotations

from dataclasses import replace
from typing import cast

import fixtures
from fixtures import (
    TRIANGLE,
    TWO_POCKET_FIBER,
    TWO_POCKET_IDS,
    synthesis_inputs_from_fiber,
    search_plan,
)
from synthesizer.model import (
    HomingCircuit,
    Homings,
    Synthesis,
    SynthesisInputs,
    ForcedCircuits,
)
from synthesizer.assemble import (
    assign_homes,
    homing_miles,
    wan_pops_physically_biconnectable,
    build_synthesis_for_wan_pops,
    forced_wan_pop_resilience_error,
)

pop = fixtures.carrier_pop
physical = fixtures.fiber_segments_from
access = fixtures.tenant_site


def _dual_inputs(s_coord: tuple[float, float] = (0.0, 0.05)) -> SynthesisInputs:
    return synthesis_inputs_from_fiber(
        ["c1", "c2"], DUAL_FIBER, {"c1", "c2"},
        [access("s", *s_coord)], coords={"c1": (0.0, 0.0), "c2": (0.0, 0.1)},
    )


def _joined(homings: Homings | None) -> list[HomingCircuit]:
    return homings.joined() if homings else []


def _homing_counts(homing_circuits: list[HomingCircuit]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for homing_circuit in homing_circuits:
        counts[homing_circuit.source] = counts.get(homing_circuit.source, 0) + 1
    return counts


def test_assign_homes_homes_a_demand_site_to_two_wan_pops() -> None:
    result = assign_homes(("c1", "c2"), _dual_inputs(), search_plan([]))
    assert _homing_counts(_joined(result)) == {"s": 2}


def test_assign_homes_returns_none_when_backbone_smaller_than_the_homing_degree() -> None:
    assert assign_homes(("c1",), _dual_inputs(), search_plan([], homing_degree=2)) is None


def test_assign_homes_homes_to_the_configured_count() -> None:
    triple_fiber = physical(
        {
            ("c1", "c2"): 1.0, ("c2", "c3"): 1.0, ("c1", "c3"): 1.0,
            ("s", "c1"): 1.0, ("s", "c2"): 1.0, ("s", "c3"): 1.0,
        }
    )
    inputs = synthesis_inputs_from_fiber(
        ["c1", "c2", "c3"], triple_fiber, {"c1", "c2", "c3"},
        [access("s", 0.0, 0.05)],
        coords={"c1": (0.0, 0.0), "c2": (0.0, 0.1), "c3": (0.0, 0.2)},
    )
    result = assign_homes(("c1", "c2", "c3"), inputs, search_plan([], homing_degree=3))
    assert _homing_counts(_joined(result)) == {"s": 3}


def test_assign_homes_leads_with_a_forced_home() -> None:
    plan = replace(search_plan([]), forced_circuits=ForcedCircuits(homes=frozenset({("s", "c2")})))
    result = assign_homes(("c1", "c2"), _dual_inputs((0.0, 0.0)), plan)
    assert {
        circuit.target for circuit in _joined(result) if circuit.source == "s"
    } == {"c1", "c2"}


def test_build_synthesis_returns_none_without_homing() -> None:
    inputs = _dual_inputs()
    plan = search_plan([], homing_degree=2)
    assert build_synthesis_for_wan_pops(("c1",), inputs, plan) is None


def test_build_synthesis_returns_none_when_wan_pops_are_not_meshed() -> None:
    fiber = physical(
        {
            ("c1", "g1"): 1.0, ("c2", "g1"): 1.0, ("c1", "g2"): 1.0, ("c2", "g2"): 1.0,
            ("c3", "z"): 1.0, ("s", "c1"): 1.0, ("s", "c2"): 1.0,
        }
    )
    inputs = synthesis_inputs_from_fiber(
        ["c1", "c2", "c3", "g1", "g2", "z"], fiber, {"c1", "c2", "c3"}, [access("s")]
    )
    assert build_synthesis_for_wan_pops(("c1", "c2", "c3"), inputs, search_plan([])) is None


def test_build_synthesis_builds_a_full_synthesis() -> None:
    synthesis = build_synthesis_for_wan_pops(("c1", "c2"), _dual_inputs(), search_plan([]))
    assert set(synthesis.wan_pop_ids if synthesis else ()) == {"c1", "c2"}


def _two_pocket_inputs() -> SynthesisInputs:
    return synthesis_inputs_from_fiber(TWO_POCKET_IDS, TWO_POCKET_FIBER, set(TWO_POCKET_IDS))


def _bowtie_inputs() -> SynthesisInputs:
    return synthesis_inputs_from_fiber(_BOWTIE_IDS, _BOWTIE_FIBER, set(_BOWTIE_IDS))


def test_physically_biconnectable_within_one_block() -> None:
    assert wan_pops_physically_biconnectable(("a", "b"), _two_pocket_inputs()) is True


def test_not_physically_biconnectable_across_a_bridge() -> None:
    assert wan_pops_physically_biconnectable(("a", "d"), _two_pocket_inputs()) is False


def test_not_physically_biconnectable_across_a_cut_city() -> None:
    assert wan_pops_physically_biconnectable(("a", "d"), _bowtie_inputs()) is False


def test_physically_biconnectable_within_one_bowtie_lobe() -> None:
    assert wan_pops_physically_biconnectable(("a", "b"), _bowtie_inputs()) is True


def test_not_biconnectable_with_no_wan_pops() -> None:
    assert wan_pops_physically_biconnectable((), _bowtie_inputs()) is False


def test_forced_resilience_error_for_forced_wan_pops_split_across_pockets() -> None:
    assert forced_wan_pop_resilience_error(
        frozenset({"a", "d"}), _two_pocket_inputs(), 2
    ) is not None


def _triangle_inputs() -> SynthesisInputs:
    return synthesis_inputs_from_fiber(["a", "b", "c"], TRIANGLE, {"a", "b", "c"})


def test_forced_resilience_error_for_a_pocket_too_small_for_the_floor() -> None:
    assert forced_wan_pop_resilience_error(frozenset({"a"}), _two_pocket_inputs(), 5) is not None


def test_forced_resilience_error_none_for_a_healthy_forced_node() -> None:
    assert forced_wan_pop_resilience_error(frozenset({"a"}), _triangle_inputs(), 2) is None


def test_forced_resilience_error_none_without_forced_wan_pops() -> None:
    assert forced_wan_pop_resilience_error(frozenset(), _triangle_inputs(), 2) is None


DUAL_FIBER = physical(
    {("c1", "c2"): 1.0, ("s", "c1"): 1.0, ("s", "c2"): 1.0}
)


_BOWTIE_FIBER = physical(
    {
        ("a", "b"): 1.0, ("b", "x"): 1.0, ("a", "x"): 1.0,
        ("x", "d"): 1.0, ("d", "e"): 1.0, ("x", "e"): 1.0,
    }
)
_BOWTIE_IDS = ["a", "b", "x", "d", "e"]


def _mixed_inputs() -> SynthesisInputs:
    return synthesis_inputs_from_fiber(
        ["c1", "c2"], DUAL_FIBER, {"c1", "c2"},
        [access("s", 0.0, 0.05)],
        [fixtures.provider_region("r", 0.0, 0.4)],
        coords={"c1": (0.0, 0.0), "c2": (0.0, 0.1)},
    )


def _mixed_homings() -> Homings:
    return cast(Homings, assign_homes(("c1", "c2"), _mixed_inputs(), search_plan([])))


def _mixed_synthesis() -> Synthesis:
    return cast(
        Synthesis,
        build_synthesis_for_wan_pops(("c1", "c2"), _mixed_inputs(), search_plan([])),
    )


def test_assign_homes_keeps_a_tenant_sites_circuits_out_of_the_provider_list() -> None:
    assert _homing_counts(_mixed_homings().tenant) == {"s": 2}


def test_assign_homes_keeps_a_provider_regions_circuits_out_of_the_tenant_list() -> None:
    assert _homing_counts(_mixed_homings().provider) == {"r": 2}


def test_a_synthesis_measures_the_tenant_miles_over_the_tenants_own_circuits_alone() -> None:
    synthesis = _mixed_synthesis()
    assert synthesis.metrics.tenant_homing_miles == homing_miles(synthesis.homings.tenant)


def test_a_synthesis_measures_the_provider_miles_over_the_provider_circuits_alone() -> None:
    synthesis = _mixed_synthesis()
    assert synthesis.metrics.provider_homing_miles == homing_miles(synthesis.homings.provider)


def test_a_provider_region_further_out_is_not_averaged_into_the_tenant_miles() -> None:
    metrics = _mixed_synthesis().metrics
    assert metrics.tenant_homing_miles < metrics.provider_homing_miles
