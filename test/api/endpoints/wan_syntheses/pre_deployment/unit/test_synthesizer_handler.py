from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict, List, cast

import pytest
from botocore.exceptions import ClientError

from store import plain
from synthesizer.input_graph import haversine_miles, segment_key
from synthesizer.model import (
    HomingCircuit,
    Homings,
    NamedCircuit,
    Synthesis,
    SynthesisArtifacts,
    SynthesisCircuit,
    SynthesisMetrics,
    ValidationReport,
)

CEILINGS = [{"id": "ashburn-va", "name": "Ashburn, VA", "ceiling": 2, "target": 3}]
RUN_PATHS = ["/wan-syntheses/1", "/wan-syntheses/1/*"]


@pytest.fixture(name="synthesizer")
def synthesizer_fixture(endpoint: Callable[..., ModuleType]) -> ModuleType:
    return endpoint("wan_syntheses", "synthesizer")


def _artifacts(loaded: Any) -> SynthesisArtifacts:
    by_name = {site.name: site for site in loaded.graph}
    ashburn, chicago, cheyenne = (
        by_name["Ashburn, VA"], by_name["Chicago, IL"], by_name["Cheyenne, WY"]
    )
    warren, provider = by_name["F.E. Warren AFB"], by_name["Provider A"]
    synthesis = Synthesis(
        wan_pop_ids=(ashburn.id, chicago.id, cheyenne.id),
        transit_ids=(),
        homings=Homings(
            tenant=[HomingCircuit(warren.id, cheyenne.id, 12.5)],
            provider=[HomingCircuit(provider.id, ashburn.id, 331.25)],
        ),
        fiber_segment_keys={
            segment_key(ashburn.id, chicago.id), segment_key(chicago.id, cheyenne.id)
        },
        drawn_circuits=[
            SynthesisCircuit(
                "backbone_mesh", ashburn.id, chicago.id, (ashburn.id, chicago.id), 599.5,
                requested_by=(warren.id,),
            ),
            SynthesisCircuit(
                "backbone_mesh", chicago.id, cheyenne.id, (chicago.id, cheyenne.id), 880.5
            ),
        ],
        metrics=SynthesisMetrics(12.5, 331.25, 1480.0, 1400.0),
    )
    validation = cast(ValidationReport, {
        "backbone_diverse_circuits_ceilings": CEILINGS,
        "backbone_mesh_independence_deficient": [],
    })
    return SynthesisArtifacts(
        loaded.graph, loaded.fiber_segments, synthesis, validation, frozenset()
    )


@pytest.fixture(name="synthesized")
def synthesized_fixture(
    synthesizer: ModuleType, monkeypatch: pytest.MonkeyPatch, store: SimpleNamespace,
    run: List[Dict[str, Any]]
) -> SimpleNamespace:
    store.items.extend(run)
    synthesized = SimpleNamespace(loaded=None, answer=None)

    def synthesize(loaded: Any) -> SynthesisArtifacts:
        synthesized.loaded = loaded
        return _artifacts(loaded)

    monkeypatch.setattr(synthesizer, "_synthesize", synthesize)
    synthesized.answer = synthesizer.lambda_handler({"synthesis": 1}, None)
    return synthesized


def _assigned(store: SimpleNamespace, position: int) -> Dict[str, Any]:
    update = store.updates[position]
    names = update["ExpressionAttributeNames"]
    values = update["ExpressionAttributeValues"]
    return {
        names[target]: plain(values[value])
        for target, _, value in (
            clause.partition(" = ")
            for clause in update["UpdateExpression"].removeprefix("SET ").split(", ")
        )
    }


def _published(store: SimpleNamespace, sort_key: str) -> Dict[str, Any]:
    puts: List[Dict[str, Any]] = store.puts
    item = next(one["Item"] for one in puts if one["Item"]["SK"]["S"] == sort_key)
    return {field: plain(value) for field, value in item.items() if field not in ("PK", "SK")}


@pytest.mark.usefixtures("synthesized")
def test_a_run_is_marked_synthesizing_before_anything_is_read(store: SimpleNamespace) -> None:
    assert _assigned(store, 0) == {"status": "synthesizing"}


@pytest.mark.usefixtures("synthesized")
def test_the_status_is_assigned_to_the_run_s_record(store: SimpleNamespace) -> None:
    assert store.updates[0]["Key"] == {"PK": {"S": "wan-syntheses"}, "SK": {"S": "1"}}


def test_a_good_build_answers_success(synthesized: SimpleNamespace) -> None:
    assert synthesized.answer == {"status": "success", "synthesis": 1}


@pytest.mark.usefixtures("synthesized")
def test_a_good_build_marks_the_run_success_last(store: SimpleNamespace) -> None:
    assert (len(store.updates), _assigned(store, 1)["status"]) == (2, "success")


@pytest.mark.usefixtures("synthesized")
def test_the_success_carries_the_miles_the_synthesis_measured(store: SimpleNamespace) -> None:
    figures = _assigned(store, 1)
    assert (figures["fiber_miles"], figures["backbone_lower_bound_miles"]) == (1480, 1400)


@pytest.mark.usefixtures("synthesized")
def test_the_success_carries_the_homing_miles_by_kind(store: SimpleNamespace) -> None:
    assert _assigned(store, 1)["homing_miles"] == {"tenant": 12.5, "provider": 331.25}


@pytest.mark.usefixtures("synthesized")
def test_the_success_carries_the_diverse_circuits_against_the_number_asked(
    store: SimpleNamespace
) -> None:
    assert _assigned(store, 1)["diverse_circuits"] == {
        "number_of_diverse_circuits": 3, "ceilings": CEILINGS, "short": [],
    }


@pytest.mark.usefixtures("synthesized")
def test_the_success_carries_the_coverage_against_the_target_the_knobs_set(
    store: SimpleNamespace
) -> None:
    coverage = _assigned(store, 1)["coverage"]
    assert (coverage["target_miles"], coverage["met"], coverage["sites_above_target"]) == (
        1200, True, 0,
    )


@pytest.mark.usefixtures("synthesized")
def test_the_coverage_measures_the_worst_haul_of_a_site_or_region_to_a_wan_pop(
    store: SimpleNamespace
) -> None:
    assert _assigned(store, 1)["coverage"]["worst_haul_miles"] == 275.6


@pytest.mark.usefixtures("synthesized")
def test_the_wan_is_published_under_the_run_in_the_four_collections(
    store: SimpleNamespace
) -> None:
    assert [one["Item"]["SK"]["S"] for one in store.puts] == [
        "wan-pops/1", "wan-pops/2", "wan-pops/3", "backbone-circuits/1", "backbone-circuits/2",
        "homing-circuits/1", "homing-circuits/2", "fiber-segments/1", "fiber-segments/2",
    ]


@pytest.mark.usefixtures("synthesized")
def test_the_wan_is_published_under_the_run_s_own_partition(store: SimpleNamespace) -> None:
    assert {one["Item"]["PK"]["S"] for one in store.puts} == {"wan-syntheses/1"}


@pytest.mark.usefixtures("synthesized")
def test_a_wan_pop_is_published_named_placed_and_with_its_carrier(
    store: SimpleNamespace
) -> None:
    assert _published(store, "wan-pops/1") == {
        "name": "Ashburn, VA", "municipality": "Ashburn", "state": "VA",
        "country": "United States", "latitude": 39.0438, "longitude": -77.4874, "carrier": "zayo",
    }


@pytest.mark.usefixtures("synthesized")
def test_a_wan_pop_two_carriers_serve_names_the_first_carrier_by_name(
    store: SimpleNamespace
) -> None:
    assert _published(store, "wan-pops/2")["carrier"] == "lumen"


@pytest.mark.usefixtures("synthesized")
def test_a_backbone_circuit_is_published_between_wan_pop_ids_along_its_route(
    store: SimpleNamespace
) -> None:
    assert _published(store, "backbone-circuits/1") == {
        "source": 1, "target": 2, "route": ["Ashburn, VA", "Chicago, IL"], "distance_miles": 599.5,
        "reason": "site_target", "requested_by": ["F.E. Warren AFB"],
    }


@pytest.mark.usefixtures("synthesized")
def test_a_region_s_homing_is_published_from_the_region_s_given_id(
    store: SimpleNamespace
) -> None:
    assert _published(store, "homing-circuits/1") == {
        "source_id": 1, "homing_kind": "provider_to_backbone", "target": 1,
        "route": ["Provider A", "Ashburn, VA"], "distance_miles": 331.25,
    }


@pytest.mark.usefixtures("synthesized")
def test_a_site_s_homing_is_published_from_the_site_s_given_id(store: SimpleNamespace) -> None:
    assert _published(store, "homing-circuits/2") == {
        "source_id": 1, "homing_kind": "tenant_to_backbone", "target": 3,
        "route": ["F.E. Warren AFB", "Cheyenne, WY"], "distance_miles": 12.5,
    }


@pytest.mark.usefixtures("synthesized")
def test_a_ridden_segment_is_published_with_its_carrier_and_both_ends_placed(
    store: SimpleNamespace
) -> None:
    published = _published(store, "fiber-segments/1")
    assert {field: value for field, value in published.items() if field != "distance_miles"} == {
        "carrier": "zayo", "a_municipality": "Ashburn", "a_state": "VA", "a_latitude": 39.0438,
        "a_longitude": -77.4874, "z_municipality": "Chicago", "z_state": "IL",
        "z_latitude": 41.8781, "z_longitude": -87.6298, "submarine": False,
    }


def test_a_ridden_segment_s_miles_are_the_haversine_between_its_ends(
    synthesized: SimpleNamespace, store: SimpleNamespace
) -> None:
    by_name = {site.name: site for site in synthesized.loaded.graph}
    miles = round(haversine_miles(by_name["Ashburn, VA"], by_name["Chicago, IL"]), 3)
    assert _published(store, "fiber-segments/1")["distance_miles"] == miles


@pytest.mark.usefixtures("synthesized")
def test_a_segment_two_carriers_own_names_the_first_carrier_by_name(
    store: SimpleNamespace
) -> None:
    assert _published(store, "fiber-segments/2")["carrier"] == "lumen"


def test_the_carrier_pops_are_merged_by_city_into_the_graph(
    synthesized: SimpleNamespace
) -> None:
    assert sorted(site.name for site in synthesized.loaded.graph) == [
        "Ashburn, VA", "Cheyenne, WY", "Chicago, IL", "F.E. Warren AFB", "Provider A",
    ]


def test_the_off_net_pops_are_loaded_apart(synthesized: SimpleNamespace) -> None:
    assert [site.name for site in synthesized.loaded.off_net] == ["Dulles, VA"]


def test_each_site_and_region_is_known_by_its_given_id(synthesized: SimpleNamespace) -> None:
    assert synthesized.loaded.given == {"site-f-e-warren-afb": 1, "provider-provider-a": 1}


def test_the_named_inputs_reach_the_parameters(synthesized: SimpleNamespace) -> None:
    params = synthesized.loaded.config.params
    assert (params.forced_wan_pop_names, params.degree_exempt_wan_pop_names) == (
        ("Ashburn, VA",), ("Chicago, IL",),
    )


def test_the_circuits_given_reach_the_operator_circuits(synthesized: SimpleNamespace) -> None:
    assert synthesized.loaded.config.operator_circuits.backbone == (
        NamedCircuit("Ashburn, VA", "Cheyenne, WY"),
    )


def test_the_record_s_scalars_reach_the_tuning(synthesized: SimpleNamespace) -> None:
    tuning = synthesized.loaded.config.params.tuning
    assert (tuning.backbone_number_of_diverse_circuits, tuning.homing_degree) == (3, 2)


@pytest.fixture(name="refused")
def refused_fixture(
    synthesizer: ModuleType, monkeypatch: pytest.MonkeyPatch, store: SimpleNamespace,
    run: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(run)

    def refuse(_loaded: Any) -> SynthesisArtifacts:
        raise ValueError("No feasible synthesis")

    monkeypatch.setattr(synthesizer, "_synthesize", refuse)
    return dict(synthesizer.lambda_handler({"synthesis": 1}, None))


def test_a_build_that_is_refused_answers_fail(refused: Dict[str, Any]) -> None:
    assert refused == {"status": "fail", "synthesis": 1}


@pytest.mark.usefixtures("refused")
def test_a_build_that_is_refused_marks_the_run_fail_with_the_reason(
    store: SimpleNamespace
) -> None:
    assert _assigned(store, 1) == {"status": "fail", "reason": "No feasible synthesis"}


@pytest.mark.usefixtures("refused")
def test_a_build_that_is_refused_publishes_nothing(store: SimpleNamespace) -> None:
    assert store.puts == []


def test_a_run_that_is_not_there_is_a_lookup_error(synthesizer: ModuleType) -> None:
    with pytest.raises(LookupError):
        synthesizer.lambda_handler({"synthesis": 7}, None)


@pytest.mark.usefixtures("synthesized")
def test_the_run_is_invalidated_once_marked_synthesizing_and_again_once_published(
    distribution: SimpleNamespace
) -> None:
    assert distribution.invalidated == [RUN_PATHS, RUN_PATHS]


@pytest.mark.usefixtures("refused")
def test_a_refused_run_is_invalidated_once_marked_synthesizing_and_again_once_marked_fail(
    distribution: SimpleNamespace
) -> None:
    assert distribution.invalidated == [RUN_PATHS, RUN_PATHS]


@pytest.fixture(name="unmarked")
def unmarked_fixture(
    synthesizer: ModuleType, store: SimpleNamespace, run: List[Dict[str, Any]]
) -> None:
    store.items.extend(run)
    store.failing = True
    with pytest.raises(ClientError):
        synthesizer.lambda_handler({"synthesis": 1}, None)


@pytest.mark.usefixtures("unmarked")
def test_a_store_that_refuses_the_first_mark_invalidates_nothing(
    distribution: SimpleNamespace
) -> None:
    assert distribution.invalidated == []
