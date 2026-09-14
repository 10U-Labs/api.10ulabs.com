import json
from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Dict, List

import pytest
from botocore.exceptions import ClientError

from lambda_http import Handler

Served = Callable[[Dict[str, Any]], Any]
SYNTHESES = "/wan-syntheses"
FIELDS = [
    "label", "wan_pop_count", "backbone_number_of_diverse_circuits", "homing_degree",
    "convergence_promotion", "knobs", "settings", "sites",
    "hyperscale_cloud_service_provider_regions", "off_net", "forced_wan_pops", "forced_circuits",
    "forced_homes", "prohibited_wan_pops", "prohibited_circuits", "degree_exempt_wan_pops",
]
WARREN = {"name": "F.E. Warren AFB", "municipality": "Cheyenne", "state": "WY",
          "country": "United States", "latitude": 41.1517, "longitude": -104.8678,
          "exempt_from_distance_constraint": False}
HILL = {"name": "Hill AFB", "municipality": "Layton", "state": "UT", "country": "United States",
        "latitude": 41.124, "longitude": -111.9731, "exempt_from_distance_constraint": True}
PROVIDER_A = {"id": 9, "name": "Provider A", "municipality": "Columbus", "state": "OH",
              "country": "United States", "latitude": 39.9612, "longitude": -82.9988}
DULLES = {"municipality": "Dulles", "state": "VA", "country": "United States",
          "latitude": 38.9519, "longitude": -77.448}
RUN = {
    "label": "minuteman",
    "wan_pop_count": {"min": 3, "max": 6},
    "backbone_number_of_diverse_circuits": 3,
    "homing_degree": 2,
    "convergence_promotion": False,
    "knobs": {"coverage_target_miles": 1200},
    "settings": {"compass_sector_count": 8, "wan_pop_search_memory_share": 0.6},
    "sites": [WARREN, HILL],
    "hyperscale_cloud_service_provider_regions": [PROVIDER_A],
    "off_net": [DULLES],
    "forced_wan_pops": ["Ashburn, VA", "Cheyenne, WY"],
    "forced_circuits": [{"source": "Ashburn, VA", "target": "Cheyenne, WY"}],
    "forced_homes": [{"source": "Hill AFB", "target": "Salt Lake City, UT"}],
    "prohibited_wan_pops": [],
    "prohibited_circuits": [{"source": "Minot, ND", "target": "Great Falls, MT"}],
    "degree_exempt_wan_pops": ["Minot, ND"],
}
RECORD = {
    "id": 3, "label": "minuteman", "wan_pop_count": {"min": 3, "max": 6},
    "backbone_number_of_diverse_circuits": 3, "homing_degree": 2, "convergence_promotion": False,
    "knobs": {"coverage_target_miles": 1200},
    "settings": {"compass_sector_count": 8, "wan_pop_search_memory_share": 0.6},
    "status": "creating",
}
BODY = "The body must be exactly the run's " + ", ".join(FIELDS)


@pytest.fixture
def handler(endpoint: Callable[..., ModuleType], monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.setenv("SYNTHESIZER", "the-synthesizer")
    return endpoint("wan_syntheses", "writer")


def _post(body: Any = None, raw: str = "") -> Dict[str, Any]:
    return {
        "resource": SYNTHESES, "httpMethod": "POST",
        "body": raw or json.dumps(RUN if body is None else body),
    }


def _without(field: str) -> Dict[str, Any]:
    return {name: value for name, value in RUN.items() if name != field}


def _sort_keys(store: SimpleNamespace) -> List[str]:
    puts: List[Dict[str, Any]] = store.puts
    return [one["Item"]["SK"]["S"] for one in puts]


def _written(store: SimpleNamespace, sort_key: str) -> Dict[str, Any]:
    puts: List[Dict[str, Any]] = store.puts
    return next(one["Item"] for one in puts if one["Item"]["SK"]["S"] == sort_key)


def test_a_full_body_answers_201(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_post())["statusCode"] == 201


def test_a_creation_is_located_at_the_synthesis_the_counter_gave(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert answer(_post())["headers"]["Location"] == "/wan-syntheses/3"


def test_a_creation_answers_the_record_with_its_id_and_status_creating(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    assert served(_post()) == RECORD


def test_a_creation_starts_the_counter_at_one_when_there_is_none(served: Served) -> None:
    assert served(_post())["id"] == 1


def test_a_creation_advances_the_syntheses_counter(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_post())
    assert store.updates[0]["Key"] == {"PK": {"S": "wan-syntheses"}, "SK": {"S": "#"}}


def test_the_record_is_written_first_under_the_collection(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_post())
    assert (store.puts[0]["Item"]["PK"], store.puts[0]["Item"]["SK"]) == (
        {"S": "wan-syntheses"}, {"S": "3"},
    )


def test_the_record_holds_the_label_the_scalar_inputs_and_status_creating(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_post())
    assert store.puts[0]["Item"] == {
        "PK": {"S": "wan-syntheses"}, "SK": {"S": "3"}, "label": {"S": "minuteman"},
        "wan_pop_count": {"M": {"min": {"N": "3"}, "max": {"N": "6"}}},
        "backbone_number_of_diverse_circuits": {"N": "3"}, "homing_degree": {"N": "2"},
        "convergence_promotion": {"BOOL": False},
        "knobs": {"M": {"coverage_target_miles": {"N": "1200"}}},
        "settings": {"M": {
            "compass_sector_count": {"N": "8"}, "wan_pop_search_memory_share": {"N": "0.6"},
        }},
        "status": {"S": "creating"},
    }


def test_every_element_of_a_list_input_is_written_under_the_synthesis_in_body_order(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_post())
    assert _sort_keys(store)[1:] == [
        "sites/1", "sites/2", "hyperscale-cloud-service-provider-regions/1", "off-net/1",
        "forced-wan-pops/1", "forced-wan-pops/2", "forced-circuits/1", "forced-homes/1",
        "prohibited-circuits/1", "degree-exempt-wan-pops/1",
    ]


def test_a_list_element_is_written_under_the_synthesis_s_own_partition(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_post())
    assert {one["Item"]["PK"]["S"] for one in store.puts[1:]} == {"wan-syntheses/3"}


def test_a_site_is_written_as_named_placed_and_exempt_or_not(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_post())
    assert _written(store, "sites/2") == {
        "PK": {"S": "wan-syntheses/3"}, "SK": {"S": "sites/2"}, "name": {"S": "Hill AFB"},
        "municipality": {"S": "Layton"}, "state": {"S": "UT"}, "country": {"S": "United States"},
        "latitude": {"N": "41.124"}, "longitude": {"N": "-111.9731"},
        "exempt_from_distance_constraint": {"BOOL": True},
    }


def test_a_region_is_written_as_the_catalog_serves_it_without_the_catalog_s_id(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_post())
    assert _written(store, "hyperscale-cloud-service-provider-regions/1") == {
        "PK": {"S": "wan-syntheses/3"}, "SK": {"S": "hyperscale-cloud-service-provider-regions/1"},
        "name": {"S": "Provider A"}, "municipality": {"S": "Columbus"}, "state": {"S": "OH"},
        "country": {"S": "United States"}, "latitude": {"N": "39.9612"},
        "longitude": {"N": "-82.9988"},
    }


def test_an_off_net_pop_is_written_as_placed(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_post())
    assert _written(store, "off-net/1") == {
        "PK": {"S": "wan-syntheses/3"}, "SK": {"S": "off-net/1"}, "municipality": {"S": "Dulles"},
        "state": {"S": "VA"}, "country": {"S": "United States"}, "latitude": {"N": "38.9519"},
        "longitude": {"N": "-77.448"},
    }


def test_a_named_pop_is_written_by_its_name(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_post())
    assert _written(store, "forced-wan-pops/2")["name"] == {"S": "Cheyenne, WY"}


def test_a_circuit_is_written_by_its_ends(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_post())
    assert _written(store, "prohibited-circuits/1") == {
        "PK": {"S": "wan-syntheses/3"}, "SK": {"S": "prohibited-circuits/1"},
        "source": {"S": "Minot, ND"}, "target": {"S": "Great Falls, MT"},
    }


def test_the_synthesizer_the_environment_names_is_invoked(
    answer: Handler, invoker: SimpleNamespace
) -> None:
    answer(_post())
    assert invoker.invocations[0]["FunctionName"] == "the-synthesizer"


def test_the_synthesizer_is_invoked_once_as_an_event(
    answer: Handler, invoker: SimpleNamespace
) -> None:
    answer(_post())
    assert [one["InvocationType"] for one in invoker.invocations] == ["Event"]


def test_the_synthesizer_is_handed_the_synthesis_s_id(
    answer: Handler, invoker: SimpleNamespace, store: SimpleNamespace,
    syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    answer(_post())
    assert json.loads(invoker.invocations[0]["Payload"]) == {"synthesis": 3}


@pytest.mark.parametrize("field", FIELDS)
def test_a_body_missing_a_field_answers_400(answer: Handler, field: str) -> None:
    assert answer(_post(_without(field)))["statusCode"] == 400


def test_a_body_missing_a_field_names_every_field(served: Served) -> None:
    assert served(_post(_without("label")))["error"] == BODY


def test_a_body_with_a_field_too_many_answers_400(answer: Handler) -> None:
    assert answer(_post({**RUN, "tenant": "minuteman"}))["statusCode"] == 400


@pytest.mark.parametrize("raw", ["[]", "not json", "\"minuteman\""])
def test_a_body_that_is_not_an_object_answers_400(answer: Handler, raw: str) -> None:
    assert answer(_post(raw=raw))["statusCode"] == 400


BAD_SCALARS = [
    ("label", 3), ("label", ""), ("wan_pop_count", {"min": "3", "max": 6}),
    ("wan_pop_count", {"min": 3}), ("wan_pop_count", [3, 6]),
    ("backbone_number_of_diverse_circuits", "3"), ("backbone_number_of_diverse_circuits", 2.5),
    ("homing_degree", True), ("convergence_promotion", "no"), ("knobs", []), ("settings", "x"),
]
BAD_ELEMENTS = [
    ("sites", [{"name": "Hill AFB"}]),
    ("sites", [{**HILL, "exempt_from_distance_constraint": "No"}]),
    ("sites", [{**HILL, "latitude": "41.124"}]), ("sites", ["Hill AFB"]),
    ("hyperscale_cloud_service_provider_regions", [{}]),
    ("hyperscale_cloud_service_provider_regions", [{**PROVIDER_A, "name": ""}]),
    ("off_net", ["Dulles"]), ("off_net", [{**DULLES, "name": "Dulles"}]),
    ("forced_wan_pops", [3]), ("forced_wan_pops", [""]), ("forced_wan_pops", "Ashburn, VA"),
    ("forced_circuits", [{"source": "a"}]), ("forced_circuits", [{"source": 1, "target": 2}]),
    ("forced_homes", ["Hill AFB"]), ("prohibited_wan_pops", [{}]),
    ("prohibited_circuits", [{"source": "a", "target": "b", "route": []}]),
    ("degree_exempt_wan_pops", [None]),
]


@pytest.mark.parametrize(("field", "value"), BAD_SCALARS + BAD_ELEMENTS)
def test_a_field_that_is_not_as_described_answers_400(
    answer: Handler, field: str, value: Any
) -> None:
    assert answer(_post({**RUN, field: value}))["statusCode"] == 400


@pytest.mark.parametrize(("field", "value"), BAD_SCALARS + BAD_ELEMENTS)
def test_a_field_that_is_not_as_described_is_named(
    served: Served, field: str, value: Any
) -> None:
    assert served(_post({**RUN, field: value}))["error"] == f"Invalid {field}"


def test_a_refused_body_writes_nothing_and_starts_nothing(
    answer: Handler, store: SimpleNamespace, invoker: SimpleNamespace
) -> None:
    answer(_post(_without("sites")))
    assert (store.updates, store.puts, invoker.invocations) == ([], [], [])


def test_a_store_that_refuses_the_creation_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_post())["statusCode"] == 500


def test_a_store_that_refuses_the_creation_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_post())["error"] == "Failed to create the wan synthesis"


def test_a_store_that_refuses_the_creation_starts_nothing(
    answer: Handler, store: SimpleNamespace, invoker: SimpleNamespace
) -> None:
    store.failing = True
    answer(_post())
    assert invoker.invocations == []


@pytest.fixture
def refusing_invoker(invoker: SimpleNamespace) -> SimpleNamespace:
    def refuse(**_request: Any) -> Dict[str, Any]:
        raise ClientError({"Error": {"Code": "ResourceNotFoundException"}}, "Invoke")
    invoker.invoke = refuse
    return invoker


@pytest.mark.usefixtures("refusing_invoker")
def test_a_synthesizer_that_cannot_be_started_answers_500(answer: Handler) -> None:
    assert answer(_post())["statusCode"] == 500


@pytest.mark.usefixtures("refusing_invoker")
def test_a_synthesizer_that_cannot_be_started_names_the_error(served: Served) -> None:
    assert served(_post())["error"] == "Failed to start the synthesis"


def test_another_route_answers_404(answer: Handler) -> None:
    assert answer({"resource": SYNTHESES, "httpMethod": "GET"})["statusCode"] == 404


SYNTHESIS = "/wan-syntheses/{synthesis}"
MISSING = "No such wan synthesis"


def _delete(synthesis: str) -> Dict[str, Any]:
    return {
        "resource": SYNTHESIS, "httpMethod": "DELETE", "pathParameters": {"synthesis": synthesis},
    }


@pytest.fixture(name="deleted")
def deleted_fixture(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> Dict[str, Any]:
    store.items.extend(syntheses)
    return answer(_delete("1"))


def test_a_finished_synthesis_is_deleted_with_204(deleted: Dict[str, Any]) -> None:
    assert deleted["statusCode"] == 204


@pytest.mark.usefixtures("deleted")
def test_a_deleted_synthesis_is_gone_with_everything_under_it(store: SimpleNamespace) -> None:
    assert [
        item["SK"]["S"] for item in store.items
        if item["PK"]["S"] in ("wan-syntheses/1",) or item["SK"]["S"] == "1"
    ] == []


@pytest.mark.usefixtures("deleted")
def test_a_deletion_leaves_the_other_syntheses_alone(store: SimpleNamespace) -> None:
    kept = sorted(item["SK"]["S"] for item in store.items if item["PK"]["S"] == "wan-syntheses")
    assert kept == ["#", "2"]


@pytest.mark.usefixtures("deleted")
def test_a_deletion_leaves_what_is_under_the_other_syntheses(store: SimpleNamespace) -> None:
    assert {item["PK"]["S"] for item in store.items} == {"wan-syntheses", "wan-syntheses/2"}


@pytest.mark.usefixtures("deleted")
def test_the_record_is_deleted_last_and_must_exist(store: SimpleNamespace) -> None:
    assert (store.deletes[-1]["Key"], store.deletes[-1]["ConditionExpression"]) == (
        {"PK": {"S": "wan-syntheses"}, "SK": {"S": "1"}}, "attribute_exists(PK)",
    )


@pytest.mark.parametrize("status", ["creating", "synthesizing"])
def test_a_synthesis_still_running_answers_409(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]], status: str
) -> None:
    store.items.extend(syntheses)
    store.items[1]["status"] = {"S": status}
    assert answer(_delete("2"))["statusCode"] == 409


def test_a_synthesis_still_running_names_the_refusal(
    served: Served, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    store.items[1]["status"] = {"S": "synthesizing"}
    assert served(_delete("2"))["error"] == "The synthesis is still running"


def test_a_synthesis_still_running_is_left_whole(
    answer: Handler, store: SimpleNamespace, syntheses: List[Dict[str, Any]]
) -> None:
    store.items.extend(syntheses)
    store.items[1]["status"] = {"S": "creating"}
    answer(_delete("2"))
    assert store.deletes == []


def test_deleting_an_unknown_synthesis_answers_404(answer: Handler) -> None:
    assert answer(_delete("3"))["statusCode"] == 404


def test_deleting_an_unknown_synthesis_names_the_error(served: Served) -> None:
    assert served(_delete("3"))["error"] == MISSING


@pytest.mark.parametrize("synthesis", ["#", "", "minuteman", "-1"])
def test_deleting_an_id_that_is_not_a_number_answers_404_and_reads_nothing(
    answer: Handler, store: SimpleNamespace, synthesis: str
) -> None:
    assert (answer(_delete(synthesis))["statusCode"], store.gets) == (404, [])


def test_a_store_that_refuses_the_deletion_answers_500(
    answer: Handler, store: SimpleNamespace
) -> None:
    store.failing = True
    assert answer(_delete("1"))["statusCode"] == 500


def test_a_store_that_refuses_the_deletion_names_the_error(
    served: Served, store: SimpleNamespace
) -> None:
    store.failing = True
    assert served(_delete("1"))["error"] == "Failed to delete the wan synthesis"
