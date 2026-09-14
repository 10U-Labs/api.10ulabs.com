from typing import Any, Callable, Dict, List, Tuple

from published_syntheses import (
    UNFINISHED,
    cut_cities,
    diverse_circuit_count,
    fiber_miles_run_over,
    homed_counts,
    homing_miles_served,
    overbuilt_pairs,
    removable_circuits,
    wan_pop_groups,
    wan_pop_names,
    worst_haul,
)

ROUNDED_TO = 0.001
SPLIT_REFUSAL = "splits the WAN at: "


def _rounding_slack(synthesis: Dict[str, Any]) -> float:
    return (len(synthesis["fiber"]) + 1) * ROUNDED_TO / 2


def _runs_outside(
    syntheses: List[Dict[str, Any]], allowed: Callable[[float, float, float], bool]
) -> Dict[str, Tuple[float, float]]:
    measured = {
        synthesis["label"]: (
            fiber_miles_run_over(synthesis), synthesis["lower_bound_miles"],
            _rounding_slack(synthesis),
        )
        for synthesis in syntheses
        if synthesis["lower_bound_miles"] is not None
    }
    return {
        label: (miles, floor)
        for label, (miles, floor, slack) in measured.items()
        if not allowed(miles, floor, slack)
    }


def _published_cities(synthesis: Dict[str, Any]) -> set[str]:
    return {wan_pop["name"] for wan_pop in synthesis["wan_pops"]}


def _refused_for_a_split(status: Dict[str, Any]) -> bool:
    return status.get("status") == "fail" and SPLIT_REFUSAL in status.get("reason", "")


def test_every_run_the_roster_declares_has_a_synthesis(
    delivered_syntheses: List[Dict[str, Any]]
) -> None:
    assert [one["label"] for one in delivered_syntheses if one["id"] is None] == []


def test_no_synthesis_is_still_creating_or_synthesizing(
    delivered_syntheses: List[Dict[str, Any]]
) -> None:
    assert [
        one["label"] for one in delivered_syntheses if one["status"].get("status") in UNFINISHED
    ] == []


def test_every_synthesis_ended_success_or_was_refused_for_a_split(
    delivered_syntheses: List[Dict[str, Any]]
) -> None:
    assert {
        one["label"]: one["status"].get("status")
        for one in delivered_syntheses
        if one["status"].get("status") != "success" and not _refused_for_a_split(one["status"])
    } == {}


def test_every_split_refusal_names_the_pop_whose_loss_would_split_the_wan(
    delivered_syntheses: List[Dict[str, Any]]
) -> None:
    assert [
        one["label"]
        for one in delivered_syntheses
        if _refused_for_a_split(one["status"])
        and not one["status"]["reason"].split(SPLIT_REFUSAL, 1)[1].strip()
    ] == []


def test_every_published_network_is_one_network(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert {
        one["label"]: groups
        for one in published_syntheses
        if len(groups := wan_pop_groups(one)) > 1
    } == {}


def test_every_published_network_reports_the_coverage_it_delivered(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert [one["label"] for one in published_syntheses if "coverage" not in one["status"]] == []


def test_every_report_is_measured_against_the_target_its_run_declares(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert {
        one["label"]: one["status"]["coverage"]["target_miles"] for one in published_syntheses
    } == {one["label"]: one["target_miles"] for one in published_syntheses}


def test_every_city_a_run_forces_is_placed_in_its_published_backbone(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert {
        one["label"]: sorted(set(one["forced"]) - _published_cities(one))
        for one in published_syntheses
        if not set(one["forced"]) <= _published_cities(one)
    } == {}


def test_the_reported_worst_haul_is_the_one_the_published_network_delivers(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert [
        (one["label"], worst_haul(one))
        for one in published_syntheses
        if worst_haul(one) != one["status"]["coverage"]["worst_haul_miles"]
    ] == []


def test_no_synthesis_missed_its_coverage_target_below_the_wan_pops_it_was_allowed(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert [
        (one["label"], len(one["wan_pops"]), one["max_wan_pop_count"])
        for one in published_syntheses
        if not one["status"]["coverage"]["met"]
        and len(one["wan_pops"]) < one["max_wan_pop_count"]
    ] == []


def test_no_published_network_leaves_a_wan_pop_short_of_the_circuits_it_was_asked_for(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert {
        one["label"]: one["status"]["diverse_circuits"]["short"]
        for one in published_syntheses
        if one["status"]["diverse_circuits"]["short"]
    } == {}


def test_no_published_network_draws_a_pair_more_circuits_than_its_run_asked_for(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert {
        one["label"]: overbuilt_pairs(one) for one in published_syntheses if overbuilt_pairs(one)
    } == {}


def test_no_published_network_holds_a_circuit_that_is_nobody_s_diverse_circuit(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert {
        one["label"]: removable_circuits(one)
        for one in published_syntheses
        if removable_circuits(one)
    } == {}


def test_no_published_network_is_split_by_the_loss_of_one_city(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert {
        one["label"]: cut_cities(one["circuits"])
        for one in published_syntheses
        if cut_cities(one["circuits"])
    } == {}


def test_no_published_network_runs_more_than_twice_the_fewest_miles_it_could_have(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert _runs_outside(published_syntheses, lambda miles, floor, _slack: miles <= 2 * floor) == {}


def test_no_published_network_runs_more_than_a_tenth_further_than_the_floor_it_publishes(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert _runs_outside(
        published_syntheses, lambda miles, floor, _slack: miles <= 1.1 * floor
    ) == {}


def test_no_published_network_runs_fewer_miles_than_the_floor_it_publishes(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert _runs_outside(
        published_syntheses, lambda miles, floor, slack: miles >= floor - slack
    ) == {}


def _credited_past_the_ceiling(synthesis: Dict[str, Any]) -> List[str]:
    names = wan_pop_names(synthesis)
    ceilings = {
        str(entry["name"]): int(entry["ceiling"])
        for entry in synthesis["status"].get("diverse_circuits", {}).get("ceilings", [])
    }
    return [
        f"{name} credited {credited} against a ceiling of {ceilings[name]}"
        for wan_pop, name in sorted(names.items(), key=lambda pair: pair[1])
        if name in ceilings
        and (credited := diverse_circuit_count(synthesis["circuits"], wan_pop, names))
        > ceilings[name]
    ]


def test_no_published_wan_pop_is_credited_more_diverse_circuits_than_its_ceiling(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert {
        one["label"]: _credited_past_the_ceiling(one)
        for one in published_syntheses
        if _credited_past_the_ceiling(one)
    } == {}


def _homed_the_wrong_number_of_times(synthesis: Dict[str, Any]) -> Dict[Tuple[str, int], int]:
    return {
        source: count
        for source, count in sorted(homed_counts(synthesis).items())
        if count != synthesis["homing_degree"]
    }


def test_every_site_and_region_holds_the_homing_circuits_its_run_asked_for(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert {
        one["label"]: _homed_the_wrong_number_of_times(one)
        for one in published_syntheses
        if _homed_the_wrong_number_of_times(one)
    } == {}


def _unhomed(synthesis: Dict[str, Any]) -> List[Tuple[str, int]]:
    given = {("tenant_to_backbone", site["id"]) for site in synthesis["sites"]} | {
        ("provider_to_backbone", region["id"]) for region in synthesis["regions"]
    }
    return sorted(given - set(homed_counts(synthesis)))


def test_every_site_and_region_a_run_was_given_is_homed(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert {one["label"]: _unhomed(one) for one in published_syntheses if _unhomed(one)} == {}


def _figure_off_its_circuits(synthesis: Dict[str, Any], kind: str) -> bool:
    published: float = synthesis["status"]["homing_miles"][kind]
    slack = (len(synthesis["homings"]) + 1) * ROUNDED_TO / 2
    return abs(published - homing_miles_served(synthesis, kind)) > slack


def test_every_published_figure_for_the_sites_is_the_miles_of_their_circuits(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert [
        one["label"] for one in published_syntheses if _figure_off_its_circuits(one, "tenant")
    ] == []


def test_every_published_figure_for_the_regions_is_the_miles_of_their_circuits(
    published_syntheses: List[Dict[str, Any]]
) -> None:
    assert [
        one["label"] for one in published_syntheses if _figure_off_its_circuits(one, "provider")
    ] == []
