import base64
import json
from types import ModuleType
from typing import Any, Dict

PAYLOAD = {"message": "hello", "number": 42, "nested": {"items": [1, 2, 3]}}


def _post(body: Any, **extra: Any) -> Dict[str, Any]:
    return {"resource": "/diagnostics/echo", "httpMethod": "POST", "body": body, **extra}


def _answer(diagnostics_handler: ModuleType, event: Dict[str, Any]) -> Dict[str, Any]:
    return dict(diagnostics_handler.lambda_handler(event, None))


def _body(diagnostics_handler: ModuleType, event: Dict[str, Any]) -> Dict[str, Any]:
    return dict(json.loads(_answer(diagnostics_handler, event)["body"]))


def test_echo_answers_200(diagnostics_handler: ModuleType) -> None:
    assert _answer(diagnostics_handler, _post(json.dumps(PAYLOAD)))["statusCode"] == 200


def test_echo_answers_json(diagnostics_handler: ModuleType) -> None:
    headers = _answer(diagnostics_handler, _post(json.dumps(PAYLOAD)))["headers"]
    assert headers["Content-Type"] == "application/json"


def test_echo_returns_the_body_it_was_sent(diagnostics_handler: ModuleType) -> None:
    assert _body(diagnostics_handler, _post(json.dumps(PAYLOAD)))["echo"] == PAYLOAD


def test_echo_decodes_a_base64_body(diagnostics_handler: ModuleType) -> None:
    encoded = base64.b64encode(json.dumps(PAYLOAD).encode("utf-8")).decode("ascii")
    assert _body(diagnostics_handler, _post(encoded, isBase64Encoded=True))["echo"] == PAYLOAD


def test_echo_names_the_request_it_received(diagnostics_handler: ModuleType) -> None:
    event = _post("{}", requestContext={"requestId": "abc-123"})
    assert _body(diagnostics_handler, event)["received_at"] == "abc-123"


def test_echo_treats_no_body_as_an_empty_object(diagnostics_handler: ModuleType) -> None:
    assert _body(diagnostics_handler, _post(None))["echo"] == {}


def test_echo_refuses_what_is_not_json_with_400(diagnostics_handler: ModuleType) -> None:
    assert _answer(diagnostics_handler, _post("not json"))["statusCode"] == 400


def test_echo_names_the_error_it_refused(diagnostics_handler: ModuleType) -> None:
    assert _body(diagnostics_handler, _post("not json"))["error"] == "Invalid JSON"


def test_another_method_answers_404(diagnostics_handler: ModuleType) -> None:
    event = {"resource": "/diagnostics/echo", "httpMethod": "GET"}
    assert _answer(diagnostics_handler, event)["statusCode"] == 404
