from __future__ import annotations

import fixtures
from synthesizer.validation import sites_below_homing_degree, validate_synthesis
from synthesizer.model import (
    Homings,
    HomingCircuit,
    Synthesis,
    MeshRequirements,
    SynthesisCircuit,
    ValidationReport,
)
from synthesizer.input_graph import Site, segment_key


def make_pop(site_id: str) -> Site:
    return Site(id=site_id, name=site_id, kind="PoP", coords=(0.0, 0.0))


def build_synthesis(
    wan_pop_ids: tuple[str, ...],
    transit_ids: tuple[str, ...],
    homing_circuits: list[HomingCircuit],
    physical_pairs: list[tuple[str, str]],
) -> Synthesis:
    return Synthesis(
        wan_pop_ids=wan_pop_ids,
        transit_ids=transit_ids,
        homings=Homings(homing_circuits, []),
        fiber_segment_keys={segment_key(left, right) for left, right in physical_pairs},
        drawn_circuits=[],
        metrics=fixtures.no_miles(),
    )


GOOD = build_synthesis(
    wan_pop_ids=("B1", "B2"),
    transit_ids=("X", "Y"),
    homing_circuits=[HomingCircuit("A", "B1", 1.0), HomingCircuit("A", "B2", 1.0)],
    physical_pairs=[("X", "B1"), ("Y", "B2"), ("B1", "B2")],
)
SINGLE_HOMED = build_synthesis(
    wan_pop_ids=("B1", "B2"),
    transit_ids=(),
    homing_circuits=[HomingCircuit("A", "B1", 1.0)],
    physical_pairs=[("B1", "B2")],
)

GOOD_SITES = [make_pop(name) for name in ("A", "X", "Y", "B1", "B2")]
SINGLE_SITES = [make_pop(name) for name in ("A", "B1", "B2")]


def test_good_synthesis_homes_demand_with_redundancy() -> None:
    report = validate_synthesis(GOOD_SITES, GOOD)
    assert report["every_site_meets_homing_degree"] is True


def test_good_synthesis_has_no_missing_redundancy() -> None:
    assert not sites_below_homing_degree(GOOD, 2)


def test_backbone_mesh_survives_any_one_link_loss_with_fewer_than_two_wan_pops() -> None:
    synthesis = build_synthesis(("B1",), (), [], [])
    report = validate_synthesis([make_pop("B1")], synthesis)
    assert report["backbone_mesh_survives_any_one_link_loss"] is True


TRIPLE_HOMED = build_synthesis(
    wan_pop_ids=("B1", "B2", "B3"),
    transit_ids=(),
    homing_circuits=[HomingCircuit("s", target, 1.0) for target in ("B1", "B2", "B3")],
    physical_pairs=[("B1", "B2")],
)
TRIPLE_HOMED_SITES = [make_pop(name) for name in ("s", "B1", "B2", "B3")]


def test_homing_passes_at_the_configured_count() -> None:
    report = validate_synthesis(TRIPLE_HOMED_SITES, TRIPLE_HOMED, homing_degree=3)
    assert report["every_site_meets_homing_degree"] is True


def test_homing_fails_above_the_configured_count() -> None:
    assert sites_below_homing_degree(TRIPLE_HOMED, 2) == ["s"]


def test_homing_fails_below_the_configured_count() -> None:
    report = validate_synthesis(SINGLE_SITES, SINGLE_HOMED)
    assert report["every_site_meets_homing_degree"] is False


def test_missing_redundancy_names_the_failing_demand_site() -> None:
    assert sites_below_homing_degree(SINGLE_HOMED, 2) == ["A"]


def _mesh_synthesis(wan_pop_ids: tuple[str, ...], pairs: list[tuple[str, str]]) -> Synthesis:
    return Synthesis(
        wan_pop_ids=wan_pop_ids,
        transit_ids=(),
        homings=Homings([], []),
        fiber_segment_keys={segment_key(left, right) for left, right in pairs},
        drawn_circuits=[
            SynthesisCircuit("backbone_mesh", left, right, (left, right), 1.0)
            for left, right in pairs
        ],
        metrics=fixtures.no_miles(),
    )


def _mesh_report(
    wan_pop_ids: tuple[str, ...],
    pairs: list[tuple[str, str]],
    backbone_number_of_diverse_circuits: int = 3,
    degree_exempt: frozenset[str] = frozenset(),
    ceilings: dict[str, int] | None = None,
) -> ValidationReport:
    return validate_synthesis(
        [make_pop(name) for name in wan_pop_ids],
        _mesh_synthesis(wan_pop_ids, pairs),
        targets=MeshRequirements(backbone_number_of_diverse_circuits, degree_exempt, ceilings),
    )


_HEALTHY = (
    ("C1", "C2", "C3", "C4", "C5"),
    [("C1", "C2"), ("C2", "C3"), ("C3", "C4"), ("C4", "C5"), ("C5", "C1"),
     ("C1", "C3"), ("C2", "C4"), ("C3", "C5")],
)
_DEFICIENT = (
    ("C1", "C2", "C3", "C4", "C5"),
    [("C1", "C2"), ("C1", "C3"), ("C1", "C4"), ("C2", "C4"), ("C2", "C5"), ("C3", "C5")],
)
_SMALL = (("C1", "C2", "C3"), [("C1", "C2"), ("C2", "C3"), ("C1", "C3")])


def test_backbone_meeting_the_target_satisfies_the_mesh_rule() -> None:
    assert _mesh_report(*_HEALTHY)["backbone_meets_mesh_link_target"] is True


def test_backbone_below_the_target_fails_the_mesh_rule() -> None:
    assert _mesh_report(*_DEFICIENT)["backbone_meets_mesh_link_target"] is False


def test_number_of_diverse_circuits_is_configurable() -> None:
    assert _mesh_report(*_DEFICIENT, backbone_number_of_diverse_circuits=2)[
        "backbone_meets_mesh_link_target"
    ] is True


def test_backbone_below_the_target_names_the_deficient_wan_pops() -> None:
    report = _mesh_report(*_DEFICIENT)
    assert {item["id"] for item in report["backbone_diverse_circuits_deficient"]} == {
        "C3", "C4", "C5"
    }


def test_exempting_every_short_wan_pop_satisfies_the_mesh_rule() -> None:
    report = _mesh_report(*_DEFICIENT, degree_exempt=frozenset({"C3", "C4", "C5"}))
    assert report["backbone_meets_mesh_link_target"] is True


def test_exempting_one_short_wan_pop_leaves_the_others_reported() -> None:
    report = _mesh_report(*_DEFICIENT, degree_exempt=frozenset({"C3"}))
    assert {item["id"] for item in report["backbone_diverse_circuits_deficient"]} == {"C4", "C5"}


def test_the_report_names_the_exempt_wan_pops() -> None:
    report = _mesh_report(*_DEFICIENT, degree_exempt=frozenset({"C3"}))
    assert report["backbone_degree_exempt"] == [{"id": "C3", "name": "C3"}]


def test_the_report_names_no_exempt_wan_pop_by_default() -> None:
    assert _mesh_report(*_HEALTHY)["backbone_degree_exempt"] == []


def test_the_report_names_a_wan_pop_whose_target_the_tool_lowered() -> None:
    report = _mesh_report(*_DEFICIENT, ceilings={"C3": 2})
    assert report["backbone_diverse_circuits_ceiling_limited"] == [
        {"id": "C3", "name": "C3", "ceiling": 2}
    ]


def test_the_report_lowers_nobody_when_the_fiber_meets_the_degree() -> None:
    assert _mesh_report(*_HEALTHY)["backbone_diverse_circuits_ceiling_limited"] == []


def test_the_report_gives_every_measured_wan_pop_its_count_and_its_target() -> None:
    report = _mesh_report(*_DEFICIENT, ceilings={"C3": 2, "C4": 4})
    assert report["backbone_diverse_circuits_ceilings"] == [
        {"id": "C3", "name": "C3", "ceiling": 2, "target": 2},
        {"id": "C4", "name": "C4", "ceiling": 4, "target": 3},
    ]


def test_the_report_measures_no_wan_pop_the_merged_carriers_said_nothing_about() -> None:
    report = _mesh_report(*_DEFICIENT, ceilings={"C3": 2})
    assert [entry["id"] for entry in report["backbone_diverse_circuits_ceilings"]] == ["C3"]


def test_small_backbone_is_exempt_from_the_mesh_rule() -> None:
    assert _mesh_report(*_SMALL)["backbone_meets_mesh_link_target"] is True


def _independence_report(circuits: list[tuple[str, ...]]) -> ValidationReport:
    return validate_synthesis(
        [make_pop(name) for name in (*fixtures.SHARED_TRANSIT_WAN_POPS, "x", "y")],
        fixtures.meshed_backbone_synthesis(circuits, fixtures.SHARED_TRANSIT_WAN_POPS),
        targets=MeshRequirements(2),
    )


def test_shared_transit_fails_the_independent_mesh_target() -> None:
    assert _independence_report(fixtures.SHARED_TRANSIT_CIRCUITS)[
        "backbone_meets_independent_mesh_link_target"
    ] is False


def test_shared_transit_names_the_wan_pop_that_falls_short() -> None:
    report = _independence_report(fixtures.SHARED_TRANSIT_CIRCUITS)
    assert {item["id"] for item in report["backbone_mesh_independence_deficient"]} == {"a"}


def test_diverse_transit_meets_the_independent_mesh_target() -> None:
    assert _independence_report(fixtures.DIVERSE_TRANSIT_CIRCUITS)[
        "backbone_meets_independent_mesh_link_target"
    ] is True


def test_healthy_backbone_survives_any_one_link_loss() -> None:
    assert _mesh_report(*_HEALTHY)["backbone_mesh_survives_any_one_link_loss"] is True


def test_bridged_backbone_is_not_survives_any_one_link_loss() -> None:
    chain = _mesh_synthesis(("C1", "C2", "C3"), [("C1", "C2"), ("C2", "C3")])
    report = validate_synthesis([make_pop(n) for n in ("C1", "C2", "C3")], chain)
    assert report["backbone_mesh_survives_any_one_link_loss"] is False


def _drawn_synthesis(
    wan_pop_ids: tuple[str, ...], drawn_circuits: list[SynthesisCircuit]
) -> Synthesis:
    return Synthesis(
        wan_pop_ids=wan_pop_ids,
        transit_ids=(),
        homings=Homings([], []),
        fiber_segment_keys=set(),
        drawn_circuits=drawn_circuits,
        metrics=fixtures.no_miles(),
    )


_SHARED_CORRIDOR = _drawn_synthesis(
    ("A", "B", "C"),
    [
        SynthesisCircuit("backbone_mesh", "A", "B", ("A", "X", "B"), 2.0),
        SynthesisCircuit("backbone_mesh", "A", "C", ("A", "X", "C"), 2.0),
        SynthesisCircuit("backbone_mesh", "B", "C", ("B", "C"), 1.0),
        SynthesisCircuit("access", "B", "C", ("B", "C"), 1.0),
    ],
)
_DISJOINT_CIRCUITS = _drawn_synthesis(
    ("A", "B"),
    [
        SynthesisCircuit("backbone_mesh", "A", "B", ("A", "B"), 1.0),
        SynthesisCircuit("backbone_mesh", "A", "B", ("A", "Y", "B"), 2.0),
    ],
)


def test_shared_physical_corridor_is_not_survives_any_one_link_loss() -> None:
    report = validate_synthesis([make_pop(n) for n in ("A", "X", "B", "C")], _SHARED_CORRIDOR)
    assert report["backbone_mesh_survives_any_one_link_loss"] is False


def test_segment_disjoint_circuits_are_survives_any_one_link_loss() -> None:
    report = validate_synthesis([make_pop(n) for n in ("A", "B", "Y")], _DISJOINT_CIRCUITS)
    assert report["backbone_mesh_survives_any_one_link_loss"] is True


def test_backbone_mesh_survives_any_one_site_loss_with_fewer_than_two_wan_pops() -> None:
    synthesis = build_synthesis(("B1",), (), [], [])
    report = validate_synthesis([make_pop("B1")], synthesis)
    assert report["backbone_mesh_survives_any_one_site_loss"] is True


def test_healthy_backbone_survives_any_one_site_loss() -> None:
    assert _mesh_report(*_HEALTHY)["backbone_mesh_survives_any_one_site_loss"] is True


def test_chain_backbone_is_not_survives_any_one_site_loss() -> None:
    chain = _mesh_synthesis(("C1", "C2", "C3"), [("C1", "C2"), ("C2", "C3")])
    report = validate_synthesis([make_pop(n) for n in ("C1", "C2", "C3")], chain)
    assert report["backbone_mesh_survives_any_one_site_loss"] is False


def test_an_undrawn_wan_pop_is_not_survives_any_one_site_loss() -> None:
    synthesis = _mesh_synthesis(("C1", "C2", "C3"), [("C1", "C2")])
    report = validate_synthesis([make_pop(n) for n in ("C1", "C2", "C3")], synthesis)
    assert report["backbone_mesh_survives_any_one_site_loss"] is False


_BOWTIE_SYNTHESIS = _drawn_synthesis(
    ("B1", "B2", "B3", "B4"),
    [
        SynthesisCircuit("backbone_mesh", "B1", "B2", ("B1", "B2"), 1.0),
        SynthesisCircuit("backbone_mesh", "B2", "H", ("B2", "H"), 1.0),
        SynthesisCircuit("backbone_mesh", "B1", "H", ("B1", "H"), 1.0),
        SynthesisCircuit("backbone_mesh", "H", "B3", ("H", "B3"), 1.0),
        SynthesisCircuit("backbone_mesh", "B3", "B4", ("B3", "B4"), 1.0),
        SynthesisCircuit("backbone_mesh", "H", "B4", ("H", "B4"), 1.0),
    ],
)
_BOWTIE_SITES = [make_pop(name) for name in ("B1", "B2", "B3", "B4", "H")]


def test_bowtie_backbone_survives_any_one_link_loss() -> None:
    report = validate_synthesis(_BOWTIE_SITES, _BOWTIE_SYNTHESIS)
    assert report["backbone_mesh_survives_any_one_link_loss"] is True


def test_bowtie_backbone_is_not_survives_any_one_site_loss() -> None:
    report = validate_synthesis(_BOWTIE_SITES, _BOWTIE_SYNTHESIS)
    assert report["backbone_mesh_survives_any_one_site_loss"] is False


_DISCONNECTED = build_synthesis(
    wan_pop_ids=("B1", "B2", "B3", "B4"),
    transit_ids=(),
    homing_circuits=[],
    physical_pairs=[("B1", "B2"), ("B3", "B4")],
)
_DISCONNECTED_SITES = [make_pop(name) for name in ("B1", "B2", "B3", "B4")]


def test_disconnected_synthesis_reports_multiple_components() -> None:
    report = validate_synthesis(_DISCONNECTED_SITES, _DISCONNECTED)
    assert report["component_count"] == 2


def test_disconnected_synthesis_skips_articulation_search() -> None:
    report = validate_synthesis(_DISCONNECTED_SITES, _DISCONNECTED)
    assert report["articulation_points"] == []


def test_degree_deficient_site_is_named() -> None:
    report = validate_synthesis(_DISCONNECTED_SITES, _DISCONNECTED)
    assert {item["id"] for item in report["degree_deficient_sites"]} == {
        "B1", "B2", "B3", "B4",
    }


def test_empty_synthesis_reports_zero_min_degree() -> None:
    empty = build_synthesis((), (), [], [])
    assert validate_synthesis([], empty)["min_distinct_neighbor_degree"] == 0


def test_articulation_point_is_flagged() -> None:
    chain = _mesh_synthesis(("C1", "C2", "C3"), [("C1", "C2"), ("C2", "C3")])
    report = validate_synthesis([make_pop(n) for n in ("C1", "C2", "C3")], chain)
    assert {item["id"] for item in report["articulation_points"]} == {"C2"}


_STUB_SEAT = (
    ("C1", "C2", "C3", "C6"),
    [("C1", "C2"), ("C2", "C3"), ("C1", "C3"), ("C1", "C6")],
)


def _cut_report(
    circuits: list[tuple[str, ...]],
    backbone_number_of_diverse_circuits: int = 2,
) -> ValidationReport:
    return validate_synthesis(
        [make_pop(name) for name in (*fixtures.SHARED_TRANSIT_WAN_POPS, "x", "y")],
        fixtures.meshed_backbone_synthesis(circuits, fixtures.SHARED_TRANSIT_WAN_POPS),
        targets=MeshRequirements(backbone_number_of_diverse_circuits),
    )


def test_a_healthy_backbone_names_no_cut_pop() -> None:
    assert _mesh_report(*_HEALTHY)["backbone_mesh_cut_pops"] == []


def test_a_healthy_backbone_survives_the_loss_of_any_one_pop() -> None:
    assert _mesh_report(*_HEALTHY)["backbone_mesh_has_no_cut_pop"] is True


def test_the_transit_pop_two_circuits_share_is_named_a_cut_pop() -> None:
    assert _cut_report(fixtures.SHARED_TRANSIT_CIRCUITS)["backbone_mesh_cut_pops"] == [
        {"id": "x", "name": "x"}
    ]


def test_a_backbone_one_pops_loss_splits_has_a_cut_pop() -> None:
    assert _cut_report(fixtures.SHARED_TRANSIT_CIRCUITS)["backbone_mesh_has_no_cut_pop"] is False


def test_circuits_over_diverse_transit_name_no_cut_pop() -> None:
    assert _cut_report(fixtures.DIVERSE_TRANSIT_CIRCUITS)["backbone_mesh_cut_pops"] == []


def test_a_tenant_asking_for_one_circuit_is_named_the_cut_pop_all_the_same() -> None:
    assert _cut_report(
        fixtures.SHARED_TRANSIT_CIRCUITS, backbone_number_of_diverse_circuits=1
    )["backbone_mesh_cut_pops"] == [{"id": "x", "name": "x"}]


def test_the_wan_pop_a_stub_circuit_hangs_off_is_named_a_cut_pop() -> None:
    assert _mesh_report(*_STUB_SEAT, backbone_number_of_diverse_circuits=2)[
        "backbone_mesh_cut_pops"
    ] == [{"id": "C1", "name": "C1"}]


def test_a_stub_circuit_ending_at_a_capped_wan_pop_still_names_the_cut_pop() -> None:
    assert _mesh_report(
        *_STUB_SEAT, backbone_number_of_diverse_circuits=2, ceilings={"C6": 1}
    )["backbone_mesh_cut_pops"] == [{"id": "C1", "name": "C1"}]


_IN_PIECES = (
    ("C1", "C2", "C3", "C4", "C5"),
    [("C1", "C2"), ("C2", "C3"), ("C4", "C5")],
)


def _named(*ids: str) -> list[dict[str, str]]:
    return [{"id": site_id, "name": site_id} for site_id in ids]


def test_a_backbone_mesh_in_pieces_names_the_wan_pops_in_each_piece() -> None:
    assert _mesh_report(*_IN_PIECES, backbone_number_of_diverse_circuits=2)[
        "backbone_mesh_pieces"
    ] == [_named("C1", "C2", "C3"), _named("C4", "C5")]


def test_a_backbone_mesh_in_pieces_is_not_one_piece() -> None:
    assert _mesh_report(*_IN_PIECES, backbone_number_of_diverse_circuits=2)[
        "backbone_mesh_is_one_piece"
    ] is False


def test_a_pop_whose_loss_cuts_a_piece_deeper_is_named_though_the_mesh_is_in_pieces() -> None:
    assert _mesh_report(*_IN_PIECES, backbone_number_of_diverse_circuits=2)[
        "backbone_mesh_cut_pops"
    ] == _named("C2")


def test_a_healthy_backbone_is_one_piece_holding_every_wan_pop() -> None:
    assert _mesh_report(*_HEALTHY)["backbone_mesh_pieces"] == [_named(*_HEALTHY[0])]


def test_a_wan_pop_no_circuit_reaches_is_a_piece_of_its_own() -> None:
    assert _mesh_report(
        ("C1", "C2", "C3"), [("C1", "C2")], backbone_number_of_diverse_circuits=2,
    )["backbone_mesh_pieces"] == [_named("C1", "C2"), _named("C3")]


def test_a_wan_in_pieces_is_in_pieces_whatever_the_tenant_asked_for() -> None:
    assert _mesh_report(*_IN_PIECES, backbone_number_of_diverse_circuits=1)[
        "backbone_mesh_is_one_piece"
    ] is False
