import json
import re
from pathlib import Path
from typing import Any, Dict, Tuple

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


def test_carriers_answers_get_and_post(openapi: Dict[str, Any]) -> None:
    assert list(openapi["paths"]["/carriers"]) == ["get", "post"]


@pytest.mark.parametrize("method", ["get", "post"])
def test_carriers_is_served_by_the_carriers_handler(openapi: Dict[str, Any], method: str) -> None:
    assert openapi["paths"]["/carriers"][method][INTEGRATION]["uri"] == "${CarriersHandlerArn}"


@pytest.mark.parametrize("method", ["get", "post"])
def test_carriers_is_reached_with_a_bearer_token(openapi: Dict[str, Any], method: str) -> None:
    assert openapi["paths"]["/carriers"][method]["security"] == [{"bearer": []}]


def test_a_carrier_is_created_from_its_name_alone(openapi: Dict[str, Any]) -> None:
    body = openapi["paths"]["/carriers"]["post"]["requestBody"]["content"]["application/json"]
    assert body["schema"]["additionalProperties"] is False


def test_a_created_carrier_is_located(openapi: Dict[str, Any]) -> None:
    created = openapi["paths"]["/carriers"]["post"]["responses"]["201"]
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
    assert _secured_operations(openapi) == {("/carriers", "get"), ("/carriers", "post")}


def test_nothing_is_secured_for_the_whole_document(openapi: Dict[str, Any]) -> None:
    assert "security" not in openapi
