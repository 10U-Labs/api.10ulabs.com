from __future__ import annotations

import fixtures
import pytest
from synthesizer.stages import DualHomed, dual_home, finalize
from synthesizer.model import SynthesisParams, Tuning, ValidationReport

_TWO_DIVERSE_CIRCUITS = Tuning(backbone_number_of_diverse_circuits=2)


def test_dual_home_returns_a_graph_without_off_net() -> None:
    homed = dual_home(
        fixtures.ring_sites(), fixtures.ring_fiber_segments(), fixtures.ring_params(), []
    )
    assert all((homed.sites, homed.fiber_segments))


def _homed_with_a_forced_off_net_pop() -> DualHomed:
    site, params = fixtures.forced_off_net_case()
    return dual_home(fixtures.ring_sites(), fixtures.ring_fiber_segments(), params, [site])


def _homed_with_a_forced_on_net_site() -> DualHomed:
    luke = fixtures.tenant_site("Luke", 40.5, -100.0)
    params = SynthesisParams(
        min_wan_pop_count=2,
        forced_wan_pop_names=("Luke",),
    )
    return dual_home(
        [*fixtures.ring_sites(), luke], fixtures.ring_fiber_segments(), params, []
    )


def test_dual_home_realizes_a_forced_off_net_pop() -> None:
    assert any(
        site.id.startswith("offnet_") for site in _homed_with_a_forced_off_net_pop().sites
    )


def test_dual_home_fabricates_a_forced_on_net_site() -> None:
    assert any(
        site.id.startswith("fac_") for site in _homed_with_a_forced_on_net_site().sites
    )


def test_dual_home_reports_the_off_net_twin_it_fabricated() -> None:
    homed = _homed_with_a_forced_off_net_pop()
    assert {
        site.id for site in homed.sites if site.id.startswith("offnet_")
    } == homed.fabricated_ids


def test_dual_home_reports_the_on_net_twin_it_fabricated() -> None:
    homed = _homed_with_a_forced_on_net_site()
    assert {
        site.id for site in homed.sites if site.id.startswith("fac_")
    } == homed.fabricated_ids


def _homed_with_a_forced_site_the_off_net_roster_also_lists() -> DualHomed:
    site, params = fixtures.forced_off_net_case()
    return dual_home(
        [*fixtures.ring_sites(), fixtures.tenant_site(site.name, *site.coords)],
        fixtures.ring_fiber_segments(),
        params,
        [site],
    )


def test_a_forced_site_the_off_net_roster_also_lists_is_realized_as_off_net() -> None:
    assert [
        site.id for site in _homed_with_a_forced_site_the_off_net_roster_also_lists().sites
        if site.id.startswith("offnet_")
    ] == ["offnet_Dulles Hub"]


def test_a_forced_site_the_off_net_roster_also_lists_is_fabricated_once() -> None:
    assert len(_homed_with_a_forced_site_the_off_net_roster_also_lists().fabricated_ids) == 1


def test_dual_home_reports_no_carrier_pop_as_fabricated() -> None:
    homed = _homed_with_a_forced_off_net_pop()
    assert not homed.fabricated_ids & {site.id for site in fixtures.ring_sites()}


def test_finalize_validates_a_synthesis() -> None:
    art = fixtures.ring_artifacts()
    _sites, _fiber, _synthesis, validation = finalize(
        art.sites, art.fiber_segments, art.synthesis, fixtures.ring_params()
    )
    assert validation["connected"] is True


def test_finalize_returns_the_synthesis_unchanged() -> None:
    art = fixtures.ring_artifacts()
    _sites, _fiber, synthesis, _validation = finalize(
        art.sites, art.fiber_segments, art.synthesis, fixtures.ring_params()
    )
    assert synthesis is art.synthesis


def test_finalize_reports_the_independent_mesh_target() -> None:
    art = fixtures.ring_artifacts()
    _sites, _fiber, _synthesis, validation = finalize(
        art.sites, art.fiber_segments, art.synthesis, fixtures.ring_params()
    )
    assert validation["backbone_meets_independent_mesh_link_target"] is True


def _finalize_short_of_three(degree_exempt: frozenset[str] = frozenset()) -> ValidationReport:
    _sites, _fiber, _synthesis, validation = finalize(
        list(fixtures.carrier_pops_by_id(fixtures.SHORT_OF_THREE_CITIES).values()),
        {},
        fixtures.meshed_backbone_synthesis(
            fixtures.SHORT_OF_THREE_CIRCUITS, fixtures.SHORT_OF_THREE_WAN_POPS
        ),
        SynthesisParams(min_wan_pop_count=2),
        degree_exempt,
    )
    return validation


def test_finalize_refuses_a_synthesis_short_of_the_configured_number_of_diverse_circuits() -> None:
    with pytest.raises(ValueError, match="independently failing backbone mesh circuits at"):
        _finalize_short_of_three()


def test_finalize_refuses_a_wan_pop_the_fiber_caps_below_two_circuits_as_a_split() -> None:
    synthesis = fixtures.meshed_backbone_synthesis(
        fixtures.SHARED_TRANSIT_CIRCUITS, fixtures.SHARED_TRANSIT_WAN_POPS
    )
    params = SynthesisParams(min_wan_pop_count=2, tuning=_TWO_DIVERSE_CIRCUITS)
    fiber = fixtures.fiber_segments_from({
        ("a", "x"): 1.0, ("x", "b"): 1.0, ("x", "c"): 1.0, ("b", "c"): 1.0,
    })
    with pytest.raises(ValueError, match="splits the WAN at: x"):
        finalize(list(fixtures.carrier_pops_by_id("abcx").values()), fiber, synthesis, params)


def test_finalize_accepts_a_synthesis_whose_only_shortfall_is_exempt() -> None:
    assert _finalize_short_of_three(frozenset({"a", "d"}))[
        "backbone_meets_independent_mesh_link_target"
    ] is True


def test_finalize_reports_the_exempt_wan_pop_it_accepted() -> None:
    assert _finalize_short_of_three(frozenset({"a", "d"}))["backbone_degree_exempt"] == [
        {"id": "a", "name": "a"}, {"id": "d", "name": "d"}
    ]


def _finalize_split_backbone() -> None:
    finalize(
        list(fixtures.carrier_pops_by_id(fixtures.SPLIT_BACKBONE_CITIES).values()),
        fixtures.fiber_segments_from(fixtures.SPLIT_BACKBONE_SEGMENTS),
        fixtures.split_backbone_synthesis(),
        SynthesisParams(min_wan_pop_count=2),
    )


def test_finalize_refuses_a_wan_whose_circuits_leave_it_in_pieces() -> None:
    with pytest.raises(ValueError, match="no circuit joins"):
        _finalize_split_backbone()


def test_the_refusal_says_how_many_pieces_the_wan_fell_into() -> None:
    with pytest.raises(ValueError, match="falls into 2 pieces"):
        _finalize_split_backbone()


def test_the_refusal_names_the_wan_pops_in_each_piece() -> None:
    with pytest.raises(ValueError, match="no circuit joins: a, b; c, d"):
        _finalize_split_backbone()


_PIECES_ROUND_A_CUT_CITIES = "abcdex"
_PIECES_ROUND_A_CUT_WAN_POPS = ("a", "b", "c", "d", "e")
_PIECES_ROUND_A_CUT_CIRCUITS: list[tuple[str, ...]] = [
    ("a", "x", "b"), ("a", "x", "c"), ("d", "e"),
]


def _pieces_round_a_cut_refusal() -> str:
    try:
        finalize(
            list(fixtures.carrier_pops_by_id(_PIECES_ROUND_A_CUT_CITIES).values()),
            fixtures.fiber_segments_from({
                ("a", "x"): 1.0, ("x", "b"): 1.0, ("x", "c"): 1.0, ("d", "e"): 1.0,
            }),
            fixtures.meshed_backbone_synthesis(
                _PIECES_ROUND_A_CUT_CIRCUITS, _PIECES_ROUND_A_CUT_WAN_POPS
            ),
            SynthesisParams(min_wan_pop_count=2, tuning=_TWO_DIVERSE_CIRCUITS),
        )
    except ValueError as refusal:
        return str(refusal)
    return ""


def test_a_wan_in_pieces_is_refused_ahead_of_a_pop_whose_loss_splits_it() -> None:
    assert "splits the WAN at" not in _pieces_round_a_cut_refusal()


def test_a_wan_in_pieces_is_refused_as_the_pieces_it_fell_into() -> None:
    assert "falls into 2 pieces no circuit joins: a, b, c; d, e" in _pieces_round_a_cut_refusal()


def _finalize_split_at_transit() -> None:
    finalize(
        list(fixtures.carrier_pops_by_id(fixtures.SPLIT_AT_TRANSIT_CITIES).values()),
        fixtures.fiber_segments_from(fixtures.SPLIT_AT_TRANSIT_SEGMENTS),
        fixtures.meshed_backbone_synthesis(
            fixtures.SHARED_TRANSIT_CIRCUITS, fixtures.SHARED_TRANSIT_WAN_POPS
        ),
        SynthesisParams(min_wan_pop_count=2, tuning=_TWO_DIVERSE_CIRCUITS),
    )


def test_finalize_refuses_a_wan_the_loss_of_one_pop_splits() -> None:
    with pytest.raises(ValueError, match="splits the WAN at"):
        _finalize_split_at_transit()


def test_the_split_refusal_names_the_pop_whose_loss_splits_the_wan() -> None:
    with pytest.raises(ValueError, match="splits the WAN at: x"):
        _finalize_split_at_transit()


def _split_refusal() -> str:
    try:
        _finalize_split_at_transit()
    except ValueError as refusal:
        return str(refusal)
    return ""


def test_a_split_wan_is_refused_ahead_of_a_wan_pop_short_of_its_diverse_circuits() -> None:
    assert "independently failing" not in _split_refusal()
