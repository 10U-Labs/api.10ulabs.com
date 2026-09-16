import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

INTEGRATION = "x-amazon-apigateway-integration"
ANY_METHOD = "x-amazon-apigateway-any-method"


def _template_variables(openapi: Dict[str, Any]) -> set[str]:
    return set(re.findall(r"\$\{(\w+)\}", json.dumps(openapi)))


def _supplied_variables(routing_dir: Path) -> set[str]:
    main_tf = (routing_dir / "main.tf").read_text(encoding="utf-8")
    block = main_tf[main_tf.index("templatefile("):]
    return set(re.findall(r"^\s+(\w+)\s+= local\.integration\.", block, re.MULTILINE))


def test_health_is_served_by_the_health_handler(openapi: Dict[str, Any]) -> None:
    assert openapi["paths"]["/health"]["get"][INTEGRATION]["uri"] == "${HealthHandlerArn}"


def test_health_is_a_lambda_proxy_integration(openapi: Dict[str, Any]) -> None:
    assert openapi["paths"]["/health"]["get"][INTEGRATION]["type"] == "aws_proxy"


def test_health_answers_get_alone(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"]["/health"]) == ["get"]


def test_every_other_route_falls_to_the_catch_all(openapi: Dict[str, Any]) -> None:
    catch_all = openapi["paths"]["/{proxy+}"][ANY_METHOD]
    assert catch_all[INTEGRATION]["uri"] == "${CatchAllHandlerArn}"


def test_the_catch_all_documents_only_a_404(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"]["/{proxy+}"][ANY_METHOD]["responses"]) == ["404"]


def test_the_catch_all_documents_the_page_a_browser_is_given(openapi: Dict[str, Any]) -> None:
    refusal = openapi["paths"]["/{proxy+}"][ANY_METHOD]["responses"]["404"]
    assert refusal["content"]["text/html"]["schema"]["type"] == "string"


def test_the_routing_stack_supplies_every_template_variable(
    openapi: Dict[str, Any], routing_dir: Path
) -> None:
    assert _template_variables(openapi) == _supplied_variables(routing_dir)


POP = "/carriers/{carrier_id}/pops/{id}"
FIBER_SEGMENTS = "/carriers/{carrier_id}/fiber-segments"
FIBER_SEGMENT = "/carriers/{carrier_id}/fiber-segments/{id}"
CARRIERS_OPERATIONS = [
    ("/carriers", "get"),
    ("/carriers", "post"),
    ("/carriers/{id}", "get"),
    ("/carriers/{id}", "put"),
    ("/carriers/{id}", "delete"),
    ("/carriers/{carrier_id}/pops", "get"),
    ("/carriers/{carrier_id}/pops", "post"),
    (POP, "get"),
    (POP, "put"),
    (POP, "delete"),
    (FIBER_SEGMENTS, "get"),
    (FIBER_SEGMENTS, "post"),
    (FIBER_SEGMENT, "get"),
    (FIBER_SEGMENT, "put"),
    (FIBER_SEGMENT, "delete"),
]
REGIONS = "/hyperscale-cloud-service-provider-regions"
REGIONS_METHODS = ["get", "post"]
REGION = "/hyperscale-cloud-service-provider-regions/{id}"
REGION_SERVINGS = ["get", "put"]
REGION_METHODS = REGION_SERVINGS + ["delete"]
A_REGION = [(REGION, method) for method in REGION_METHODS]
REGIONS_OPERATIONS = [(REGIONS, method) for method in REGIONS_METHODS] + A_REGION
SYNTHESES = "/wan-syntheses"
SYNTHESIS = "/wan-syntheses/{id}"
WAN_POPS = "/wan-syntheses/{synthesis_id}/wan-pops"
WAN_POP = "/wan-syntheses/{synthesis_id}/wan-pops/{id}"
BACKBONE_CIRCUITS = "/wan-syntheses/{synthesis_id}/backbone-circuits"
HOMING_CIRCUITS = "/wan-syntheses/{synthesis_id}/homing-circuits"
RIDDEN_FIBER = "/wan-syntheses/{synthesis_id}/fiber-segments"
SITES = "/wan-syntheses/{synthesis_id}/sites"
SITE = "/wan-syntheses/{synthesis_id}/sites/{id}"
RUN_REGIONS = "/wan-syntheses/{synthesis_id}/hyperscale-cloud-service-provider-regions"
RUN_REGION = f"{RUN_REGIONS}/{{id}}"
OFF_NET = "/wan-syntheses/{synthesis_id}/off-net"
FORCED_WAN_POPS = "/wan-syntheses/{synthesis_id}/forced-wan-pops"
FORCED_CIRCUITS = "/wan-syntheses/{synthesis_id}/forced-circuits"
FORCED_HOMES = "/wan-syntheses/{synthesis_id}/forced-homes"
PROHIBITED_WAN_POPS = "/wan-syntheses/{synthesis_id}/prohibited-wan-pops"
PROHIBITED_CIRCUITS = "/wan-syntheses/{synthesis_id}/prohibited-circuits"
DEGREE_EXEMPT_WAN_POPS = "/wan-syntheses/{synthesis_id}/degree-exempt-wan-pops"
NAMED_INPUT_FIELDS = ["id", "name"]
ENDS_INPUT_FIELDS = ["id", "source", "target"]
UNDER_A_SITE = [(SITE, "get")]
UNDER_A_RUN_REGION = [(RUN_REGION, "get")]
A_SYNTHESIS = [(SYNTHESIS, "get"), (SYNTHESIS, "delete")]
UNDER_A_SYNTHESIS = [
    (WAN_POPS, "get"),
    (BACKBONE_CIRCUITS, "get"),
    (HOMING_CIRCUITS, "get"),
    (RIDDEN_FIBER, "get"),
    (SITES, "get"),
    (RUN_REGIONS, "get"),
    (OFF_NET, "get"),
    (FORCED_WAN_POPS, "get"),
    (FORCED_CIRCUITS, "get"),
    (FORCED_HOMES, "get"),
    (PROHIBITED_WAN_POPS, "get"),
    (PROHIBITED_CIRCUITS, "get"),
    (DEGREE_EXEMPT_WAN_POPS, "get"),
]
GIVEN = [
    SITES, RUN_REGIONS, RUN_REGION, OFF_NET, FORCED_WAN_POPS, FORCED_CIRCUITS, FORCED_HOMES,
    PROHIBITED_WAN_POPS, PROHIBITED_CIRCUITS, DEGREE_EXEMPT_WAN_POPS,
]
SITE_FIELDS = [
    "id", "name", "municipality", "state", "country", "latitude", "longitude",
    "exempt_from_distance_constraint",
]
RIDDEN_FIBER_FIELDS = [
    "id", "carrier", "a_municipality", "a_state", "a_latitude", "a_longitude",
    "z_municipality", "z_state", "z_latitude", "z_longitude", "distance_miles", "submarine",
]
CIRCUIT_FIELDS = ["id", "source", "target", "route", "distance_miles", "reason", "requested_by"]
HOMING_FIELDS = ["id", "source_id", "homing_kind", "target", "route", "distance_miles"]
HOMING_KINDS = ["tenant_to_backbone", "provider_to_backbone"]
UNDER_A_WAN_POP = [(WAN_POP, "get")]
WAN_POP_FIELDS = [
    "id", "name", "municipality", "state", "country", "latitude", "longitude", "carrier"
]
READINGS = [(SYNTHESES, "get"), (SYNTHESIS, "get")] + UNDER_A_SYNTHESIS + (
    UNDER_A_WAN_POP + UNDER_A_SITE + UNDER_A_RUN_REGION
)
WRITINGS = [(SYNTHESES, "post"), (SYNTHESIS, "delete")]
SYNTHESES_OPERATIONS = READINGS + WRITINGS
RUN_FIELDS = [
    "label", "wan_pop_count", "backbone_number_of_diverse_circuits", "homing_degree",
    "convergence_promotion", "knobs", "settings", "sites",
    "hyperscale_cloud_service_provider_regions", "off_net", "forced_wan_pops", "forced_circuits",
    "forced_homes", "prohibited_wan_pops", "prohibited_circuits", "degree_exempt_wan_pops",
]
NAMED_LISTS = ["forced_wan_pops", "prohibited_wan_pops", "degree_exempt_wan_pops"]
ENDED_LISTS = ["forced_circuits", "forced_homes", "prohibited_circuits"]
SYNTHESIS_FIELDS = [
    "id", "label", "wan_pop_count", "backbone_number_of_diverse_circuits", "homing_degree",
    "convergence_promotion", "knobs", "settings", "status",
]
STATUSES = ["creating", "synthesizing", "success", "fail", "timeout"]
SECURED = CARRIERS_OPERATIONS + REGIONS_OPERATIONS + SYNTHESES_OPERATIONS
CARRIER_METHODS = ["get", "put", "delete"]
POPS_METHODS = ["get", "post"]
POP_SERVINGS = ["get", "put"]
POP_METHODS = POP_SERVINGS + ["delete"]
FIBER_SEGMENTS_METHODS = ["get", "post"]
FIBER_SEGMENT_SERVINGS = ["get", "put"]
FIBER_SEGMENT_METHODS = FIBER_SEGMENT_SERVINGS + ["delete"]
A_CARRIER = [("/carriers/{id}", method) for method in CARRIER_METHODS]
UNDER_A_CARRIER = [("/carriers/{carrier_id}/pops", method) for method in POPS_METHODS] + [
    (FIBER_SEGMENTS, method) for method in FIBER_SEGMENTS_METHODS
]
UNDER_A_POP = [(POP, method) for method in POP_METHODS]
UNDER_A_FIBER_SEGMENT = [(FIBER_SEGMENT, method) for method in FIBER_SEGMENT_METHODS]
ONE_OF_A_COLLECTION = A_CARRIER + A_REGION + A_SYNTHESIS
IN_THE_PATH = [(path, method, ["id"]) for path, method in ONE_OF_A_COLLECTION] + [
    (path, method, ["carrier_id"]) for path, method in UNDER_A_CARRIER
] + [(path, method, ["carrier_id", "id"]) for path, method in UNDER_A_POP] + [
    (path, method, ["carrier_id", "id"]) for path, method in UNDER_A_FIBER_SEGMENT
] + [(path, method, ["synthesis_id"]) for path, method in UNDER_A_SYNTHESIS] + [
    (path, method, ["synthesis_id", "id"]) for path, method in UNDER_A_WAN_POP
] + [(path, method, ["synthesis_id", "id"]) for path, method in UNDER_A_SITE] + [
    (path, method, ["synthesis_id", "id"]) for path, method in UNDER_A_RUN_REGION
]
POP_FIELDS = ["id", "municipality", "state", "country", "latitude", "longitude"]
REGION_FIELDS = ["id", "name", "municipality", "state", "country", "latitude", "longitude"]
LISTED = [
    (SYNTHESES, ["id", "label"]),
    (WAN_POPS, WAN_POP_FIELDS),
    (BACKBONE_CIRCUITS, CIRCUIT_FIELDS),
    (HOMING_CIRCUITS, HOMING_FIELDS),
    (RIDDEN_FIBER, RIDDEN_FIBER_FIELDS),
    (SITES, SITE_FIELDS),
    (RUN_REGIONS, REGION_FIELDS),
    (OFF_NET, POP_FIELDS),
    (FORCED_WAN_POPS, NAMED_INPUT_FIELDS),
    (FORCED_CIRCUITS, ENDS_INPUT_FIELDS),
    (FORCED_HOMES, ENDS_INPUT_FIELDS),
    (PROHIBITED_WAN_POPS, NAMED_INPUT_FIELDS),
    (PROHIBITED_CIRCUITS, ENDS_INPUT_FIELDS),
    (DEGREE_EXEMPT_WAN_POPS, NAMED_INPUT_FIELDS),
]
SERVED = [
    (SYNTHESIS, SYNTHESIS_FIELDS),
    (WAN_POP, WAN_POP_FIELDS),
    (SITE, SITE_FIELDS),
    (RUN_REGION, REGION_FIELDS),
]
FIBER_SEGMENT_FIELDS = [
    "id", "a_municipality", "a_state", "z_municipality", "z_state", "submarine"
]
NAMED_BODIES = [("/carriers", "post"), ("/carriers/{id}", "put")]
PLACED_BODIES = [("/carriers/{carrier_id}/pops", "post"), (POP, "put")]
SPANNED_BODIES = [(FIBER_SEGMENTS, "post"), (FIBER_SEGMENT, "put")]
LOCATED_BODIES = [(REGIONS, "post"), (REGION, "put")]
MEMBER_BODIES = [(path, method, POP_FIELDS) for path, method in PLACED_BODIES] + [
    (path, method, FIBER_SEGMENT_FIELDS) for path, method in SPANNED_BODIES
] + [(path, method, REGION_FIELDS) for path, method in LOCATED_BODIES]
NAMED_ENDS = [
    (path, method, field) for path, method in PLACED_BODIES for field in ["municipality", "country"]
] + [
    (path, method, field)
    for path, method in SPANNED_BODIES for field in ["a_municipality", "z_municipality"]
] + [
    (path, method, field)
    for path, method in LOCATED_BODIES for field in ["name", "municipality", "country"]
]
OPTIONAL_STATES = [(path, method, "state") for path, method in PLACED_BODIES + LOCATED_BODIES] + [
    (path, method, field) for path, method in SPANNED_BODIES for field in ["a_state", "z_state"]
]
ADDITIONS = [
    ("/carriers/{carrier_id}/pops", "post", POP_FIELDS),
    (FIBER_SEGMENTS, "post", FIBER_SEGMENT_FIELDS),
    (REGIONS, "post", REGION_FIELDS),
]
CREATIONS = [("/carriers", "post"), (SYNTHESES, "post")] + [
    (path, method) for path, method, _ in ADDITIONS
]
DELETIONS = [
    ("/carriers/{id}", "delete"),
    (POP, "delete"),
    (FIBER_SEGMENT, "delete"),
    (REGION, "delete"),
    (SYNTHESIS, "delete"),
]


def test_carriers_answers_get_and_post(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"]["/carriers"]) == ["get", "post"]


def test_a_carrier_answers_get_put_and_delete(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"]["/carriers/{id}"]) == CARRIER_METHODS


def test_the_pops_of_a_carrier_answer_get_and_post(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"]["/carriers/{carrier_id}/pops"]) == POPS_METHODS


def test_a_pop_is_a_located_municipality_with_an_id(openapi: Dict[str, Any]) -> None:
    listed = openapi["paths"]["/carriers/{carrier_id}/pops"]["get"]["responses"]["200"]
    assert listed["content"]["application/json"]["schema"]["items"]["required"] == POP_FIELDS


def test_the_fiber_segments_of_a_carrier_answer_get_and_post(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"][FIBER_SEGMENTS]) == FIBER_SEGMENTS_METHODS


def _request_body(openapi: Dict[str, Any], path: str, method: str) -> Dict[str, Any]:
    body = openapi["paths"][path][method]["requestBody"]
    schema: Dict[str, Any] = body["content"]["application/json"]["schema"]
    return schema


def _listed_fiber_segment(openapi: Dict[str, Any]) -> Dict[str, Any]:
    listed = openapi["paths"][FIBER_SEGMENTS]["get"]["responses"]["200"]
    schema: Dict[str, Any] = listed["content"]["application/json"]["schema"]["items"]
    return schema


def _served_fiber_segment(openapi: Dict[str, Any], method: str) -> Dict[str, Any]:
    served = openapi["paths"][FIBER_SEGMENT][method]["responses"]["200"]
    schema: Dict[str, Any] = served["content"]["application/json"]["schema"]
    return schema


def _fiber_segment_schemas(openapi: Dict[str, Any]) -> List[Dict[str, Any]]:
    added = openapi["paths"][FIBER_SEGMENTS]["post"]["responses"]["201"]
    return [
        _listed_fiber_segment(openapi),
        added["content"]["application/json"]["schema"],
    ] + [_served_fiber_segment(openapi, method) for method in FIBER_SEGMENT_SERVINGS] + [
        _request_body(openapi, path, method) for path, method in SPANNED_BODIES
    ]


def test_a_fiber_segment_is_a_span_between_two_municipalities_with_an_id(
    openapi: Dict[str, Any]
) -> None:
    assert _listed_fiber_segment(openapi)["required"] == FIBER_SEGMENT_FIELDS


@pytest.mark.parametrize("method", FIBER_SEGMENT_SERVINGS)
def test_a_fiber_segment_is_served_as_a_span_between_two_municipalities_with_an_id(
    openapi: Dict[str, Any], method: str
) -> None:
    assert _served_fiber_segment(openapi, method)["required"] == FIBER_SEGMENT_FIELDS


def test_a_fiber_segment_says_whether_it_is_submarine(openapi: Dict[str, Any]) -> None:
    submarine = [one["properties"]["submarine"]["type"] for one in _fiber_segment_schemas(openapi)]
    assert submarine == ["boolean"] * 6


def test_a_fiber_segment_answers_get_put_and_delete(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"][FIBER_SEGMENT]) == FIBER_SEGMENT_METHODS


def test_a_pop_answers_get_put_and_delete(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"][POP]) == POP_METHODS


@pytest.mark.parametrize("method", POP_SERVINGS)
def test_a_pop_is_served_as_a_located_municipality_with_an_id(
    openapi: Dict[str, Any], method: str
) -> None:
    served = openapi["paths"][POP][method]["responses"]["200"]
    assert served["content"]["application/json"]["schema"]["required"] == POP_FIELDS


@pytest.mark.parametrize(("path", "method", "fields"), MEMBER_BODIES)
def test_a_member_is_written_as_itself_without_an_id(
    openapi: Dict[str, Any], path: str, method: str, fields: List[str]
) -> None:
    assert _request_body(openapi, path, method)["required"] == fields[1:]


@pytest.mark.parametrize(("path", "method"), PLACED_BODIES + SPANNED_BODIES + LOCATED_BODIES)
def test_a_member_is_written_with_no_other_field(
    openapi: Dict[str, Any], path: str, method: str
) -> None:
    assert _request_body(openapi, path, method)["additionalProperties"] is False


@pytest.mark.parametrize(("path", "method", "field"), NAMED_ENDS)
def test_a_municipality_or_a_country_a_member_is_written_with_is_named(
    openapi: Dict[str, Any], path: str, method: str, field: str
) -> None:
    assert _request_body(openapi, path, method)["properties"][field]["minLength"] == 1


@pytest.mark.parametrize(("path", "method", "field"), OPTIONAL_STATES)
def test_a_member_may_be_written_with_no_state(
    openapi: Dict[str, Any], path: str, method: str, field: str
) -> None:
    assert "minLength" not in _request_body(openapi, path, method)["properties"][field]


@pytest.mark.parametrize(("path", "method"), PLACED_BODIES + SPANNED_BODIES + LOCATED_BODIES)
def test_a_member_written_wrongly_is_documented_as_400(
    openapi: Dict[str, Any], path: str, method: str
) -> None:
    assert "400" in openapi["paths"][path][method]["responses"]


@pytest.mark.parametrize(("path", "method", "fields"), ADDITIONS)
def test_an_added_member_answers_with_its_id(
    openapi: Dict[str, Any], path: str, method: str, fields: List[str]
) -> None:
    created = openapi["paths"][path][method]["responses"]["201"]
    assert created["content"]["application/json"]["schema"]["required"] == fields


@pytest.mark.parametrize(("path", "method"), DELETIONS)
def test_a_deletion_answers_204(openapi: Dict[str, Any], path: str, method: str) -> None:
    assert "204" in openapi["paths"][path][method]["responses"]


@pytest.mark.parametrize(("path", "method"), DELETIONS)
def test_a_deletion_answers_no_content(openapi: Dict[str, Any], path: str, method: str) -> None:
    assert "content" not in openapi["paths"][path][method]["responses"]["204"]


@pytest.mark.parametrize(("path", "method"), CARRIERS_OPERATIONS)
def test_carriers_is_served_by_the_carriers_handler(
    openapi: Dict[str, Any], path: str, method: str
) -> None:
    assert openapi["paths"][path][method][INTEGRATION]["uri"] == "${CarriersHandlerArn}"


@pytest.mark.parametrize(("path", "method"), REGIONS_OPERATIONS)
def test_the_regions_are_served_by_the_regions_handler(
    openapi: Dict[str, Any], path: str, method: str
) -> None:
    uri = openapi["paths"][path][method][INTEGRATION]["uri"]
    assert uri == "${HyperscaleCloudServiceProviderRegionsHandlerArn}"


def test_the_regions_answer_get_and_post(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"][REGIONS]) == REGIONS_METHODS


def test_a_region_is_a_named_and_located_municipality_with_an_id(openapi: Dict[str, Any]) -> None:
    listed = openapi["paths"][REGIONS]["get"]["responses"]["200"]
    assert listed["content"]["application/json"]["schema"]["items"]["required"] == REGION_FIELDS


@pytest.mark.parametrize(("path", "method"), READINGS)
def test_the_syntheses_are_served_by_the_syntheses_handler(
    openapi: Dict[str, Any], path: str, method: str
) -> None:
    assert openapi["paths"][path][method][INTEGRATION]["uri"] == "${WanSynthesesHandlerArn}"


@pytest.mark.parametrize(("path", "method"), WRITINGS)
def test_the_syntheses_are_written_by_the_writer(
    openapi: Dict[str, Any], path: str, method: str
) -> None:
    assert openapi["paths"][path][method][INTEGRATION]["uri"] == "${WanSynthesesWriterHandlerArn}"


def test_a_synthesis_answers_get_and_delete(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"][SYNTHESIS]) == ["get", "delete"]


def test_a_synthesis_still_running_is_documented_as_409(openapi: Dict[str, Any]) -> None:
    assert "409" in openapi["paths"][SYNTHESIS]["delete"]["responses"]


def test_the_syntheses_answer_get_and_post(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"][SYNTHESES]) == ["get", "post"]


@pytest.mark.parametrize(
    "path", [path for path, _ in READINGS if path not in (SYNTHESES, SYNTHESIS)]
)
def test_a_path_under_the_syntheses_answers_get_alone(openapi: Dict[str, Any], path: str) -> None:
    assert list(openapi["paths"][path]) == ["get"]


def test_a_run_is_created_from_its_label_its_scalars_and_its_nine_lists(
    openapi: Dict[str, Any]
) -> None:
    assert _request_body(openapi, SYNTHESES, "post")["required"] == RUN_FIELDS


def test_a_run_is_created_with_no_other_field(openapi: Dict[str, Any]) -> None:
    assert _request_body(openapi, SYNTHESES, "post")["additionalProperties"] is False


@pytest.mark.parametrize("field", NAMED_LISTS)
def test_a_named_list_input_is_a_list_of_names(openapi: Dict[str, Any], field: str) -> None:
    items = _request_body(openapi, SYNTHESES, "post")["properties"][field]["items"]
    assert (items["type"], items["minLength"]) == ("string", 1)


@pytest.mark.parametrize("field", ENDED_LISTS)
def test_an_ended_list_input_is_a_list_of_source_and_target(
    openapi: Dict[str, Any], field: str
) -> None:
    items = _request_body(openapi, SYNTHESES, "post")["properties"][field]["items"]
    assert items["required"] == ["source", "target"]


def test_a_site_is_given_named_placed_and_exempt_or_not(openapi: Dict[str, Any]) -> None:
    items = _request_body(openapi, SYNTHESES, "post")["properties"]["sites"]["items"]
    assert items["required"] == SITE_FIELDS[1:]


def test_a_region_is_given_as_the_catalog_serves_it(openapi: Dict[str, Any]) -> None:
    field = "hyperscale_cloud_service_provider_regions"
    items = _request_body(openapi, SYNTHESES, "post")["properties"][field]["items"]
    assert items["required"] == REGION_FIELDS[1:]


def test_an_off_net_pop_is_given_placed(openapi: Dict[str, Any]) -> None:
    items = _request_body(openapi, SYNTHESES, "post")["properties"]["off_net"]["items"]
    assert items["required"] == POP_FIELDS[1:]


def test_a_creation_answers_the_record_creating(openapi: Dict[str, Any]) -> None:
    created = openapi["paths"][SYNTHESES]["post"]["responses"]["201"]
    assert created["content"]["application/json"]["schema"]["required"] == SYNTHESIS_FIELDS


def test_a_creation_refuses_a_body_it_cannot_take(openapi: Dict[str, Any]) -> None:
    assert "400" in openapi["paths"][SYNTHESES]["post"]["responses"]


def _served(openapi: Dict[str, Any], path: str) -> Dict[str, Any]:
    served = openapi["paths"][path]["get"]["responses"]["200"]
    schema: Dict[str, Any] = served["content"]["application/json"]["schema"]
    return schema


def _listed(openapi: Dict[str, Any], path: str) -> Dict[str, Any]:
    items: Dict[str, Any] = _served(openapi, path)["items"]
    return items


@pytest.mark.parametrize(("path", "fields"), LISTED)
def test_a_listing_under_the_syntheses_lists_its_fields_with_an_id(
    openapi: Dict[str, Any], path: str, fields: List[str]
) -> None:
    assert _listed(openapi, path)["required"] == fields


@pytest.mark.parametrize(("path", "fields"), SERVED)
def test_a_member_under_the_syntheses_is_served_with_its_fields_and_an_id(
    openapi: Dict[str, Any], path: str, fields: List[str]
) -> None:
    assert _served(openapi, path)["required"] == fields


def test_a_synthesis_s_status_is_one_of_five(openapi: Dict[str, Any]) -> None:
    assert _served(openapi, SYNTHESIS)["properties"]["status"]["enum"] == STATUSES


def test_a_backbone_circuit_s_route_is_the_names_it_runs_through(openapi: Dict[str, Any]) -> None:
    route = _listed(openapi, BACKBONE_CIRCUITS)["properties"]["route"]
    assert (route["type"], route["items"]["type"]) == ("array", "string")


def test_a_homing_circuit_s_kind_says_whose_id_its_source_is(openapi: Dict[str, Any]) -> None:
    kind = _listed(openapi, HOMING_CIRCUITS)["properties"]["homing_kind"]
    assert kind["enum"] == HOMING_KINDS


def test_a_ridden_fiber_segment_says_whether_it_is_submarine(openapi: Dict[str, Any]) -> None:
    assert _listed(openapi, RIDDEN_FIBER)["properties"]["submarine"]["type"] == "boolean"


@pytest.mark.parametrize("path", GIVEN)
def test_an_input_is_there_whatever_the_run_s_status(openapi: Dict[str, Any], path: str) -> None:
    missing = openapi["paths"][path]["get"]["responses"]["404"]["description"]
    assert missing.startswith("No synthesis has that id")


def test_a_region_answers_get_put_and_delete(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"][REGION]) == REGION_METHODS


@pytest.mark.parametrize("method", REGION_SERVINGS)
def test_a_region_is_served_as_a_named_and_located_municipality_with_an_id(
    openapi: Dict[str, Any], method: str
) -> None:
    served = openapi["paths"][REGION][method]["responses"]["200"]
    assert served["content"]["application/json"]["schema"]["required"] == REGION_FIELDS


@pytest.mark.parametrize(("path", "method"), SECURED)
def test_a_secured_operation_is_reached_with_a_bearer_token(
    openapi: Dict[str, Any], path: str, method: str
) -> None:
    assert openapi["paths"][path][method]["security"] == [{"bearer": []}]


@pytest.mark.parametrize(("path", "method", "names"), IN_THE_PATH)
def test_a_member_is_named_by_its_ids_in_the_path(
    openapi: Dict[str, Any], path: str, method: str, names: List[str]
) -> None:
    parameters = openapi["paths"][path][method]["parameters"]
    named = [(one["name"], one["in"], one["required"]) for one in parameters]
    assert named == [(name, "path", True) for name in names]


@pytest.mark.parametrize(("path", "method", "names"), IN_THE_PATH)
def test_an_id_in_the_path_is_a_positive_integer(
    openapi: Dict[str, Any], path: str, method: str, names: List[str]
) -> None:
    schemas = [one["schema"] for one in openapi["paths"][path][method]["parameters"]]
    assert [(one["type"], one["minimum"]) for one in schemas] == [("integer", 1)] * len(names)


def test_a_path_that_ends_in_a_parameter_ends_in_id(openapi: Dict[str, Any]) -> None:
    endings = {path.rsplit("/", 1)[1] for path in openapi["paths"]}
    assert {end for end in endings if end.startswith("{")} == {"{id}", "{proxy+}"}


def test_a_parameter_that_holds_more_path_is_a_named_id(openapi: Dict[str, Any]) -> None:
    holders = re.findall(r"\{([^}]+)\}/", "\n".join(openapi["paths"]))
    assert {holder.rsplit("_", 1)[1] for holder in holders} == {"id"}


@pytest.mark.parametrize(
    ("path", "method"),
    [(path, method) for path, method, _names in IN_THE_PATH],
)
def test_a_member_that_is_not_there_is_documented_as_404(
    openapi: Dict[str, Any], path: str, method: str
) -> None:
    assert "404" in openapi["paths"][path][method]["responses"]


@pytest.mark.parametrize(("path", "method"), NAMED_BODIES)
def test_a_carrier_is_named_by_its_name_alone(
    openapi: Dict[str, Any], path: str, method: str
) -> None:
    body = openapi["paths"][path][method]["requestBody"]["content"]["application/json"]
    assert body["schema"]["additionalProperties"] is False


@pytest.mark.parametrize(("path", "method"), CREATIONS)
def test_a_creation_is_located(openapi: Dict[str, Any], path: str, method: str) -> None:
    created = openapi["paths"][path][method]["responses"]["201"]
    assert list(created["headers"]) == ["Location"]


def test_the_bearer_scheme_is_the_authorizer(openapi: Dict[str, Any]) -> None:
    scheme = openapi["components"]["securitySchemes"]["bearer"]
    assert scheme["x-amazon-apigateway-authorizer"]["authorizerUri"] == "${AuthorizerHandlerArn}"


def test_the_authorizer_reads_the_token_alone(openapi: Dict[str, Any]) -> None:
    scheme = openapi["components"]["securitySchemes"]["bearer"]
    assert scheme["x-amazon-apigateway-authorizer"]["type"] == "token"


def test_the_authorizer_is_asked_only_for_a_bearer_token(openapi: Dict[str, Any]) -> None:
    scheme = openapi["components"]["securitySchemes"]["bearer"]
    assert scheme["x-amazon-apigateway-authorizer"]["identityValidationExpression"] == "^Bearer .+$"


def _secured_operations(openapi: Dict[str, Any]) -> set[Tuple[str, str]]:
    return {
        (path, method)
        for path, operations in openapi["paths"].items()
        for method, operation in operations.items()
        if "security" in operation
    }


def test_every_route_the_site_calls_stays_public(openapi: Dict[str, Any]) -> None:
    assert _secured_operations(openapi) == set(SECURED)


@pytest.mark.parametrize(("path", "method"), SECURED)
def test_every_secured_operation_documents_the_authorizer_s_refusals(
    openapi: Dict[str, Any], path: str, method: str
) -> None:
    assert {"401", "403"} <= set(openapi["paths"][path][method]["responses"])


def test_nothing_is_secured_for_the_whole_document(openapi: Dict[str, Any]) -> None:
    assert "security" not in openapi
