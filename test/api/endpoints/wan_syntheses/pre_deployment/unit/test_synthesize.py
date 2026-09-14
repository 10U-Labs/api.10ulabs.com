from __future__ import annotations

from dataclasses import replace

import pytest

import fixtures
from fixtures import (
    TRIANGLE,
    TWO_POCKET_FIBER,
    TWO_POCKET_IDS,
    synthesis_inputs_from_fiber,
    search_plan,
)
from synthesizer.input_graph import segment_key
from synthesizer.model import (
    Homings,
    Synthesis,
    SynthesisInputs,
    SynthesisMetrics,
    SynthesisParams,
    ForcedCircuits,
    RoleExclusions,
    RoleOverrides,
    Tuning,
)
from synthesizer.survivable import FiberInputs, FiberSelection, select_fiber
from synthesizer.synthesize import (
    wan_pop_combination_count,
    wan_pop_combinations,
    best_wan_pops_at_size,
    build_search_plan,
    convergence_promotion_ids,
    compute_eligible_wan_pop_ids,
    enumeration_limit,
    search_best_synthesis,
    synthesize_two_tier,
    total_memory_bytes,
)
from synthesizer.search_plan import _SearchPlan
from synthesizer.graphs import build_adjacency
from synthesizer.overrides import apply_role_overrides
from synthesizer.strength import site_straightness

pop = fixtures.carrier_pop
physical = fixtures.fiber_segments_from
access = fixtures.tenant_site
TRIANGLE_SITES = [pop("a"), pop("b"), pop("c"), access("s", 40.0, -99.0)]


_ONE_NODE = SynthesisParams(
    min_wan_pop_count=1,
    max_wan_pop_count=1,
    promote_high_degree_convergences=False,
    tuning=Tuning(backbone_number_of_diverse_circuits=1, homing_degree=1),
)


def test_min_wan_pop_count_below_one_is_rejected() -> None:
    with pytest.raises(ValueError):
        synthesize_two_tier(
            TRIANGLE_SITES, TRIANGLE, SynthesisParams(min_wan_pop_count=0)
        )


def test_a_tenant_asking_for_one_wan_pop_gets_the_one_it_forced() -> None:
    synthesis = synthesize_two_tier(
        TRIANGLE_SITES, TRIANGLE, _ONE_NODE,
        RoleOverrides(forced_wan_pop_ids=frozenset({"a"})),
    )
    assert synthesis.wan_pop_ids == ("a",)


def test_max_wan_pop_count_below_min_is_rejected() -> None:
    with pytest.raises(ValueError):
        synthesize_two_tier(
            TRIANGLE_SITES, TRIANGLE, SynthesisParams(min_wan_pop_count=3, max_wan_pop_count=2)
        )


def test_forced_wan_pops_exceeding_max_count_is_rejected() -> None:
    with pytest.raises(ValueError):
        synthesize_two_tier(
            TRIANGLE_SITES, TRIANGLE,
            SynthesisParams(min_wan_pop_count=2, max_wan_pop_count=2),
            RoleOverrides(forced_wan_pop_ids=frozenset({"a", "b", "c"})),
        )


def test_unknown_pop_ids_are_rejected() -> None:
    with pytest.raises(ValueError):
        synthesize_two_tier(
            [pop("a"), pop("b")], physical({("a", "c"): 1.0}), SynthesisParams()
        )


def test_pop_without_fiber_segments_is_rejected() -> None:
    with pytest.raises(ValueError):
        synthesize_two_tier(
            [pop("a"), pop("b"), pop("c")], physical({("a", "b"): 1.0}), SynthesisParams()
        )


def test_not_enough_eligible_pops_is_rejected() -> None:
    with pytest.raises(ValueError):
        synthesize_two_tier(
            [pop("a"), pop("b")], physical({("a", "b"): 1.0}),
            SynthesisParams(),
        )


def test_synthesizes_ring_to_a_feasible_synthesis() -> None:
    synthesis = synthesize_two_tier(
        fixtures.ring_sites(), fixtures.ring_fiber_segments(), fixtures.ring_params()
    )
    assert len(synthesis.wan_pop_ids) >= 2


def test_min_wan_pop_count_is_the_floor_when_feasible() -> None:
    synthesis = synthesize_two_tier(
        fixtures.ring_sites(), fixtures.ring_fiber_segments(),
        SynthesisParams(min_wan_pop_count=3),
    )
    assert len(synthesis.wan_pop_ids) == 3


def test_backbone_grows_past_the_floor_to_select_more_forced_wan_pops() -> None:
    synthesis = synthesize_two_tier(
        fixtures.ring_sites(), fixtures.ring_fiber_segments(),
        SynthesisParams(min_wan_pop_count=2),
        RoleOverrides(forced_wan_pop_ids=frozenset({"P1", "P3", "P5"})),
    )
    assert len(synthesis.wan_pop_ids) == 3


def test_no_feasible_synthesis_is_rejected() -> None:
    fiber = physical({("x1", "b1"): 1.0, ("b1", "y1"): 1.0, ("x2", "b2"): 1.0, ("b2", "y2"): 1.0})
    sites = [pop(name) for name in ("x1", "b1", "y1", "x2", "b2", "y2")]
    with pytest.raises(ValueError):
        synthesize_two_tier(
            sites, fiber,
            SynthesisParams(min_wan_pop_count=2),
        )


def test_honors_a_forced_wan_pop_override() -> None:
    synthesis = synthesize_two_tier(
        fixtures.ring_sites(), fixtures.ring_fiber_segments(),
        SynthesisParams(min_wan_pop_count=2),
        RoleOverrides(forced_wan_pop_ids=frozenset({"P3"})),
    )
    assert "P3" in synthesis.wan_pop_ids


def test_synthesize_promotes_a_convergence_hub() -> None:
    synthesis = fixtures.convergence_hub_artifacts().synthesis
    assert "hub_dc" in synthesis.wan_pop_ids


_UNPROMOTED_CONVERGENCE = fixtures.convergence_hub_artifacts(promote_convergences=False).synthesis


def test_promotion_disabled_leaves_a_convergence_hub_transit() -> None:
    assert "hub_dc" not in _UNPROMOTED_CONVERGENCE.wan_pop_ids


_CAPPED_CONVERGENCE = fixtures.convergence_hub_artifacts(max_wan_pop_count=4).synthesis


def test_backbone_cap_blocks_a_convergence_promotion() -> None:
    assert "hub_dc" not in _CAPPED_CONVERGENCE.wan_pop_ids


def test_capped_convergence_synthesis_fills_its_backbone_budget() -> None:
    assert len(_CAPPED_CONVERGENCE.wan_pop_ids) == 4


def test_eligible_excludes_a_degree_one_spur() -> None:
    fiber = physical({("a", "b"): 1.0, ("b", "c"): 1.0, ("c", "a"): 1.0, ("a", "spur"): 1.0})
    pops = [pop(name) for name in ("a", "b", "c", "spur")]
    eligible = compute_eligible_wan_pop_ids(
        pops, build_adjacency(fiber)
    )
    assert "spur" not in eligible


def test_eligible_includes_a_degree_two_pop() -> None:
    fiber = physical({("a", "b"): 1.0, ("b", "c"): 1.0, ("c", "a"): 1.0})
    pops = [pop(name) for name in ("a", "b", "c")]
    eligible = compute_eligible_wan_pop_ids(pops, build_adjacency(fiber))
    assert eligible == {"a", "b", "c"}


def _synthesis(
    wan_pop_ids: tuple[str, ...],
    fiber_segment_keys: set[tuple[str, str]],
) -> Synthesis:
    return Synthesis(
        wan_pop_ids=wan_pop_ids,
        transit_ids=(),
        homings=Homings([], []),
        fiber_segment_keys=fiber_segment_keys,
        drawn_circuits=[],
        metrics=SynthesisMetrics(0.0, 0.0, 0.0),
    )


def test_convergence_promotes_a_transit_hub() -> None:
    keys = {segment_key("hub", n) for n in ("b1", "b2", "x", "y")}
    synthesis = _synthesis(("b1", "b2"), keys)
    assert convergence_promotion_ids(synthesis) == {"hub"}


def test_convergence_skips_a_two_line_crossing() -> None:
    keys = {segment_key("mid", "b1"), segment_key("mid", "b2")}
    synthesis = _synthesis(("b1", "b2"), keys)
    assert convergence_promotion_ids(synthesis) == set()


def test_convergence_excludes_a_selected_wan_pop() -> None:
    keys = {segment_key("b1", n) for n in ("b2", "x", "y")}
    synthesis = _synthesis(("b1", "b2"), keys)
    assert convergence_promotion_ids(synthesis) == set()


def test_site_straightness_is_zero_without_reachable_sites() -> None:
    assert site_straightness("a", {"a": pop("a")}, {}) == 0.0


def test_site_straightness_skips_zero_length_hops() -> None:
    by_id = {"a": pop("a", 0.0, 0.0), "b": pop("b", 0.0, 0.0)}
    assert site_straightness("a", by_id, {"b": "a"}) == 0.0


MESH_FIBER = physical(
    {
        ("a", "b"): 1.0, ("a", "c"): 1.0, ("a", "d"): 1.0,
        ("b", "c"): 1.0, ("b", "d"): 1.0, ("c", "d"): 1.0,
        ("s", "a"): 1.0, ("s", "b"): 1.0, ("s", "c"): 1.0, ("s", "d"): 1.0,
    }
)
MESH_COORDS = {"a": (0.0, 1.0), "b": (0.0, 2.0), "c": (0.0, 50.0), "d": (0.0, 51.0)}


def _mesh_inputs() -> SynthesisInputs:
    return synthesis_inputs_from_fiber(
        ["a", "b", "c", "d"], MESH_FIBER, {"a", "b", "c", "d"},
        [access("s", 0.0, 0.0)], coords=MESH_COORDS,
    )


@pytest.mark.parametrize(
    "strength",
    [
        {"a": 10.0, "b": 10.0, "c": 1.0, "d": 1.0},
        {"a": 10.0, "b": 10.0, "c": 10.0, "d": 10.0},
    ],
)
def test_best_wan_pops_at_size_selects_strongest_then_least_last_mile(
    strength: dict[str, float],
) -> None:
    plan = search_plan(["a", "b", "c", "d"], strength=strength)
    selected = best_wan_pops_at_size(_mesh_inputs(), plan, 2)
    assert set(selected or ()) == {"a", "b"}


def test_best_wan_pops_at_size_returns_none_when_nothing_feasible() -> None:
    fiber = physical({("c1", "x"): 1.0, ("c2", "y"): 1.0})
    inputs = synthesis_inputs_from_fiber(["c1", "c2", "x", "y"], fiber, {"c1", "c2"}, [access("s")])
    assert best_wan_pops_at_size(inputs, search_plan(["c1", "c2"]), 2) is None


def test_required_wan_pops_is_fixed_into_every_set() -> None:
    forced = ForcedCircuits(required_wan_pops=frozenset({"a"}))
    plan = search_plan(["a", "b", "c"], forced_circuits=forced)
    assert wan_pop_combinations(plan, 2) == [("a", "b"), ("a", "c")]


def test_wan_pop_combinations_empty_when_size_below_required() -> None:
    forced = ForcedCircuits(required_wan_pops=frozenset({"a", "b"}))
    plan = search_plan(["a", "b"], forced_circuits=forced)
    assert wan_pop_combinations(plan, 1) == []


def test_wan_pop_combination_count_zero_when_size_below_required() -> None:
    forced = ForcedCircuits(required_wan_pops=frozenset({"a", "b"}))
    plan = search_plan(["a", "b"], forced_circuits=forced)
    assert wan_pop_combination_count(plan, 1) == 0


def test_enumeration_limit_grows_with_available_memory() -> None:
    params = SynthesisParams()
    assert enumeration_limit(32 * 10**9, params) > enumeration_limit(16 * 10**9, params)


def test_total_memory_honors_the_lambda_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_MEMORY_SIZE", "8192")
    assert total_memory_bytes() == 8192 * 1024 * 1024


def test_total_memory_falls_back_to_physical_ram(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AWS_LAMBDA_FUNCTION_MEMORY_SIZE", raising=False)
    assert total_memory_bytes() > 0


def test_search_refuses_a_space_too_large_for_memory() -> None:
    inputs = synthesis_inputs_from_fiber([], {}, set(), [])
    plan = search_plan([f"c{index}" for index in range(40)])
    with pytest.raises(ValueError):
        search_best_synthesis(inputs, SynthesisParams(min_wan_pop_count=20), plan)


def test_search_raises_when_no_size_is_feasible() -> None:
    fiber = physical({("c1", "x"): 1.0, ("c2", "y"): 1.0})
    inputs = synthesis_inputs_from_fiber(["c1", "c2", "x", "y"], fiber, {"c1", "c2"}, [access("s")])
    plan = search_plan(["c1", "c2"])
    with pytest.raises(ValueError):
        search_best_synthesis(inputs, SynthesisParams(min_wan_pop_count=2), plan)


def test_build_search_plan_ranks_candidates_by_strength() -> None:
    fiber = physical({("a", "b"): 1.0, ("b", "c"): 1.0, ("a", "c"): 1.0})
    inputs = synthesis_inputs_from_fiber(["a", "b", "c"], fiber, {"a", "b", "c"})
    plan = build_search_plan(inputs, {"a", "b", "c"}, RoleOverrides(), SynthesisParams())
    assert set(plan.wan_pop_candidates) == {"a", "b", "c"}


def test_build_search_plan_fixes_promoted_wan_pops_into_required() -> None:
    fiber = physical({("a", "b"): 1.0, ("b", "c"): 1.0, ("a", "c"): 1.0})
    inputs = synthesis_inputs_from_fiber(["a", "b", "c"], fiber, {"a", "b", "c"})
    overrides = RoleOverrides(forced_wan_pop_ids=frozenset({"a"}))
    plan = build_search_plan(
        inputs, {"a", "b", "c"}, overrides, SynthesisParams(), frozenset({"b"})
    )
    assert plan.required_wan_pops == frozenset({"a", "b"})


def _far_demand_inputs_plan(exempt: bool = False) -> tuple[SynthesisInputs, _SearchPlan]:
    fiber = physical(
        {
            ("cc1", "cw"): 1.0, ("cc2", "cw"): 1.0, ("ce", "cc2"): 1.0, ("ce", "cc1"): 1.0,
            ("cc2", "cc1"): 1.0,
            ("aw1", "cc1"): 1.0, ("aw1", "cc2"): 1.0, ("aw2", "cc1"): 1.0, ("aw2", "cc2"): 1.0,
            ("ae1", "cc1"): 1.0, ("ae1", "cc2"): 1.0, ("ae2", "cc1"): 1.0, ("ae2", "cc2"): 1.0,
        }
    )
    coords = {
        "cc1": (44.0, -100.0), "cc2": (44.0, -96.0),
        "cw": (40.0, -118.0), "ce": (40.0, -78.0),
    }
    ids = ["cc1", "cc2", "cw", "ce"]
    tenant_sites = [
        access("aw1", 40.0, -120.3), access("aw2", 40.3, -119.7),
        access("ae1", 40.0, -76.3), access("ae2", 40.3, -75.7),
    ]
    if exempt:
        tenant_sites = [
            replace(site, exempt_from_distance_constraint=True) for site in tenant_sites
        ]
    inputs = synthesis_inputs_from_fiber(
        ids, fiber, {"cc1", "cc2", "cw", "ce"}, tenant_sites, coords=coords
    )
    plan = search_plan(
        ["cc1", "cc2", "cw", "ce"],
        strength={"cc1": 3.0, "cc2": 3.0, "cw": 1.0, "ce": 1.0},
    )
    return inputs, plan


def _fiber_selections(monkeypatch: pytest.MonkeyPatch, target_miles: int) -> int:
    inputs, plan = _far_demand_inputs_plan()
    params = SynthesisParams(
        min_wan_pop_count=2,
        tuning=Tuning(backbone_coverage_target_miles=target_miles),
    )
    counted: list[tuple[str, ...]] = []

    def counting(fiber_inputs: FiberInputs) -> FiberSelection:
        counted.append(fiber_inputs.wan_pop_ids)
        return select_fiber(fiber_inputs)

    monkeypatch.setattr("synthesizer.backbone.select_fiber", counting)
    search_best_synthesis(inputs, params, plan)
    return len(counted)


def test_a_search_that_grows_past_the_floor_still_selects_its_fiber_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _fiber_selections(monkeypatch, 300) == 1


def test_a_search_that_adds_no_wan_pop_past_the_floor_selects_its_fiber_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _fiber_selections(monkeypatch, 100_000) == 1


def test_search_holds_at_the_floor_under_a_permissive_target() -> None:
    inputs, plan = _far_demand_inputs_plan()
    params = SynthesisParams(
        min_wan_pop_count=2,
        tuning=Tuning(backbone_coverage_target_miles=100_000),
    )
    assert search_best_synthesis(inputs, params, plan).wan_pop_ids == ("cc1", "cc2")


def test_search_grows_past_the_floor_to_cover_far_demand() -> None:
    inputs, plan = _far_demand_inputs_plan()
    params = SynthesisParams(
        min_wan_pop_count=2,
        tuning=Tuning(backbone_coverage_target_miles=300),
    )
    selected = set(search_best_synthesis(inputs, params, plan).wan_pop_ids)
    assert selected == {"cc1", "cc2", "cw", "ce"}


def test_exempt_demand_does_not_drive_coverage_growth() -> None:
    inputs, plan = _far_demand_inputs_plan(exempt=True)
    params = SynthesisParams(
        min_wan_pop_count=2,
        tuning=Tuning(backbone_coverage_target_miles=300),
    )
    assert search_best_synthesis(inputs, params, plan).wan_pop_ids == ("cc1", "cc2")


def test_search_exhausts_its_candidates_under_an_unreachable_target() -> None:
    inputs, plan = _far_demand_inputs_plan()
    params = SynthesisParams(
        min_wan_pop_count=2,
        tuning=Tuning(backbone_coverage_target_miles=1),
    )
    selected = set(search_best_synthesis(inputs, params, plan).wan_pop_ids)
    assert selected == {"cc1", "cc2", "cw", "ce"}


def test_max_wan_pop_count_caps_coverage_growth() -> None:
    inputs, plan = _far_demand_inputs_plan()
    params = SynthesisParams(
        min_wan_pop_count=2, max_wan_pop_count=3,
        tuning=Tuning(backbone_coverage_target_miles=300),
    )
    assert len(search_best_synthesis(inputs, params, plan).wan_pop_ids) == 3


def test_search_holds_at_the_floor_when_the_only_candidate_is_infeasible() -> None:
    fiber = physical(
        {
            ("c1", "c2"): 1.0, ("s", "c1"): 1.0, ("s", "c2"): 1.0, ("p", "q"): 1.0,
        }
    )
    coords = {
        "c1": (40.0, -100.0), "c2": (40.0, -99.0), "p": (40.0, -81.0),
    }
    inputs = synthesis_inputs_from_fiber(
        ["c1", "c2", "p", "q"], fiber, {"c1", "c2", "p"}, [access("s", 40.0, -80.5)], coords=coords
    )
    plan = search_plan(["c1", "c2", "p"], strength={"c1": 3.0, "c2": 3.0, "p": 1.0})
    params = SynthesisParams(
        min_wan_pop_count=2,
        tuning=Tuning(backbone_coverage_target_miles=300),
    )
    assert search_best_synthesis(inputs, params, plan).wan_pop_ids == ("c1", "c2")


def test_synthesize_rejects_forced_wan_pops_split_across_pockets() -> None:
    sites = [pop(name) for name in TWO_POCKET_IDS]
    params = SynthesisParams(
        min_wan_pop_count=2,
        forced_wan_pop_names=("a", "d"),
    )
    pinned, fiber, overrides = apply_role_overrides(sites, TWO_POCKET_FIBER, params)
    with pytest.raises(ValueError):
        synthesize_two_tier(pinned, fiber, params, overrides)


def test_apply_role_overrides_resolves_a_forced_wan_pop_pin() -> None:
    params = SynthesisParams(forced_wan_pop_names=("a",))
    _sites, _fiber, overrides = apply_role_overrides(
        [pop("a"), pop("b")], physical({("a", "b"): 1.0}), params
    )
    assert overrides.forced_wan_pop_ids == frozenset({"a"})


def test_apply_role_overrides_rejects_a_forced_and_prohibited_pop() -> None:
    params = SynthesisParams(
        forced_wan_pop_names=("a",),
        exclusions=RoleExclusions(prohibited_wan_pop_names=("a",)),
    )
    with pytest.raises(ValueError):
        apply_role_overrides([pop("a"), pop("b")], physical({("a", "b"): 1.0}), params)
