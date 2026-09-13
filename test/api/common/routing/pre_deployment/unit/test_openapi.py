import json
import re
from pathlib import Path
from typing import Any, Dict

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
