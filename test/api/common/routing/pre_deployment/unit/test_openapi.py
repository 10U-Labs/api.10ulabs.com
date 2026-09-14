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


def test_the_routing_stack_supplies_every_template_variable(
    openapi: Dict[str, Any], routing_dir: Path
) -> None:
    assert _template_variables(openapi) == _supplied_variables(routing_dir)


POP = "/carriers/{carrier}/pops/{pop}"
CARRIERS_OPERATIONS = [
    ("/carriers", "get"),
    ("/carriers", "post"),
    ("/carriers/{carrier}", "get"),
    ("/carriers/{carrier}", "put"),
    ("/carriers/{carrier}", "delete"),
    ("/carriers/{carrier}/pops", "get"),
    ("/carriers/{carrier}/pops", "post"),
    (POP, "get"),
    (POP, "put"),
]
CARRIER_METHODS = ["get", "put", "delete"]
POPS_METHODS = ["get", "post"]
POP_METHODS = ["get", "put"]
UNDER_A_CARRIER = [("/carriers/{carrier}", method) for method in CARRIER_METHODS] + [
    ("/carriers/{carrier}/pops", method) for method in POPS_METHODS
]
UNDER_A_POP = [(POP, method) for method in POP_METHODS]
IN_THE_PATH = [(path, method, ["carrier"]) for path, method in UNDER_A_CARRIER] + [
    (path, method, ["carrier", "pop"]) for path, method in UNDER_A_POP
]
POP_FIELDS = ["id", "municipality", "state", "country", "latitude", "longitude"]
NAMED_BODIES = [("/carriers", "post"), ("/carriers/{carrier}", "put")]
PLACED_BODIES = [("/carriers/{carrier}/pops", "post"), (POP, "put")]
CREATIONS = [("/carriers", "post"), ("/carriers/{carrier}/pops", "post")]


def test_carriers_answers_get_and_post(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"]["/carriers"]) == ["get", "post"]


def test_a_carrier_answers_get_put_and_delete(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"]["/carriers/{carrier}"]) == CARRIER_METHODS


def test_the_pops_of_a_carrier_answer_get_and_post(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"]["/carriers/{carrier}/pops"]) == POPS_METHODS


def test_a_pop_is_a_located_municipality_with_an_id(openapi: Dict[str, Any]) -> None:
    listed = openapi["paths"]["/carriers/{carrier}/pops"]["get"]["responses"]["200"]
    assert listed["content"]["application/json"]["schema"]["items"]["required"] == POP_FIELDS


def test_a_pop_answers_get_and_put(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"][POP]) == POP_METHODS


@pytest.mark.parametrize("method", POP_METHODS)
def test_a_pop_is_served_as_a_located_municipality_with_an_id(
    openapi: Dict[str, Any], method: str
) -> None:
    served = openapi["paths"][POP][method]["responses"]["200"]
    assert served["content"]["application/json"]["schema"]["required"] == POP_FIELDS


def _pop_body(openapi: Dict[str, Any], path: str, method: str) -> Dict[str, Any]:
    body = openapi["paths"][path][method]["requestBody"]
    schema: Dict[str, Any] = body["content"]["application/json"]["schema"]
    return schema


@pytest.mark.parametrize(("path", "method"), PLACED_BODIES)
def test_a_pop_is_placed_as_a_located_municipality_without_an_id(
    openapi: Dict[str, Any], path: str, method: str
) -> None:
    assert _pop_body(openapi, path, method)["required"] == POP_FIELDS[1:]


@pytest.mark.parametrize(("path", "method"), PLACED_BODIES)
def test_a_pop_is_placed_with_no_other_field(
    openapi: Dict[str, Any], path: str, method: str
) -> None:
    assert _pop_body(openapi, path, method)["additionalProperties"] is False


@pytest.mark.parametrize(("path", "method"), PLACED_BODIES)
@pytest.mark.parametrize("field", ["municipality", "country"])
def test_a_pop_is_placed_with_a_municipality_and_a_country_that_are_named(
    openapi: Dict[str, Any], path: str, method: str, field: str
) -> None:
    assert _pop_body(openapi, path, method)["properties"][field]["minLength"] == 1


@pytest.mark.parametrize(("path", "method"), PLACED_BODIES)
def test_a_pop_may_be_placed_with_no_state(
    openapi: Dict[str, Any], path: str, method: str
) -> None:
    assert "minLength" not in _pop_body(openapi, path, method)["properties"]["state"]


@pytest.mark.parametrize(("path", "method"), PLACED_BODIES)
def test_a_misplaced_pop_is_documented_as_400(
    openapi: Dict[str, Any], path: str, method: str
) -> None:
    assert "400" in openapi["paths"][path][method]["responses"]


def test_an_added_pop_answers_with_its_id(openapi: Dict[str, Any]) -> None:
    created = openapi["paths"]["/carriers/{carrier}/pops"]["post"]["responses"]["201"]
    assert created["content"]["application/json"]["schema"]["required"] == POP_FIELDS


def test_a_deleted_carrier_answers_204(openapi: Dict[str, Any]) -> None:
    assert "204" in openapi["paths"]["/carriers/{carrier}"]["delete"]["responses"]


def test_a_deleted_carrier_answers_no_content(openapi: Dict[str, Any]) -> None:
    assert "content" not in openapi["paths"]["/carriers/{carrier}"]["delete"]["responses"]["204"]


@pytest.mark.parametrize(("path", "method"), CARRIERS_OPERATIONS)
def test_carriers_is_served_by_the_carriers_handler(
    openapi: Dict[str, Any], path: str, method: str
) -> None:
    assert openapi["paths"][path][method][INTEGRATION]["uri"] == "${CarriersHandlerArn}"


@pytest.mark.parametrize(("path", "method"), CARRIERS_OPERATIONS)
def test_carriers_is_reached_with_a_bearer_token(
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


@pytest.mark.parametrize(("path", "method"), UNDER_A_CARRIER + UNDER_A_POP)
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
    assert _secured_operations(openapi) == set(CARRIERS_OPERATIONS)


@pytest.mark.parametrize(("path", "method"), CARRIERS_OPERATIONS)
def test_every_secured_operation_documents_the_authorizer_s_refusals(
    openapi: Dict[str, Any], path: str, method: str
) -> None:
    assert {"401", "403"} <= set(openapi["paths"][path][method]["responses"])


def test_nothing_is_secured_for_the_whole_document(openapi: Dict[str, Any]) -> None:
    assert "security" not in openapi
