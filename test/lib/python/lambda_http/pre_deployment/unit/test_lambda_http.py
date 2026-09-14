import base64
import json
from types import SimpleNamespace
from typing import Any, Dict

import pytest

import lambda_http
from lambda_http import (
    aws_client, created, dispatch, json_response, parse_body, parse_fields, parse_object
)


def _echo(event: Dict[str, Any]) -> Dict[str, Any]:
    return json_response(200, event['body'])


def test_json_response_carries_the_status_code() -> None:
    assert json_response(201, {})['statusCode'] == 201


def test_json_response_is_json() -> None:
    assert json_response(200, {})['headers']['Content-Type'] == 'application/json'


def test_json_response_serialises_the_body() -> None:
    assert json.loads(json_response(200, {'a': [1, 2]})['body']) == {'a': [1, 2]}


def test_created_answers_201() -> None:
    assert created('/a/1', {})['statusCode'] == 201


def test_created_locates_what_it_answers() -> None:
    assert created('/a/1', {})['headers']['Location'] == '/a/1'


def test_created_is_json() -> None:
    assert created('/a/1', {})['headers']['Content-Type'] == 'application/json'


def test_created_serialises_the_body() -> None:
    assert json.loads(created('/a/1', {'id': 1})['body']) == {'id': 1}


def test_parse_body_reads_json() -> None:
    assert parse_body({'body': '{"a": 1}'}) == {'a': 1}


def test_parse_body_reads_an_absent_body_as_empty() -> None:
    assert parse_body({'body': None}) == {}


def test_parse_body_decodes_base64() -> None:
    encoded = base64.b64encode(b'{"a": 1}').decode('ascii')
    assert parse_body({'body': encoded, 'isBase64Encoded': True}) == {'a': 1}


def test_parse_body_refuses_what_is_not_json() -> None:
    with pytest.raises(ValueError):
        parse_body({'body': 'not json'})


def test_parse_object_reads_a_json_object() -> None:
    assert parse_object({'body': '{"a": 1}'}) == {'a': 1}


def test_parse_object_refuses_what_is_not_json() -> None:
    assert parse_object({'body': 'not json'}) is None


def test_parse_object_refuses_a_json_value_that_is_not_an_object() -> None:
    assert parse_object({'body': '[1, 2]'}) is None


def test_parse_object_refuses_base64_that_is_not_utf_8() -> None:
    encoded = base64.b64encode(b'\xff').decode('ascii')
    assert parse_object({'body': encoded, 'isBase64Encoded': True}) is None


def test_parse_fields_reads_an_object_of_exactly_the_fields() -> None:
    assert parse_fields({'body': '{"a": 1, "b": 2}'}, ('b', 'a')) == {'a': 1, 'b': 2}


def test_parse_fields_refuses_an_object_missing_a_field() -> None:
    assert parse_fields({'body': '{"a": 1}'}, ('a', 'b')) is None


def test_parse_fields_refuses_an_object_with_another_field() -> None:
    assert parse_fields({'body': '{"a": 1, "b": 2}'}, ('a',)) is None


def test_parse_fields_refuses_a_json_value_that_is_not_an_object() -> None:
    assert parse_fields({'body': '["a"]'}, ('a',)) is None


def test_dispatch_calls_the_handler_of_the_resource_and_method() -> None:
    event = {'resource': '/a', 'httpMethod': 'POST', 'body': 'x'}
    assert dispatch(event, {('/a', 'POST'): _echo})['body'] == '"x"'


def test_dispatch_answers_404_for_another_method() -> None:
    event = {'resource': '/a', 'httpMethod': 'GET'}
    assert dispatch(event, {('/a', 'POST'): _echo})['statusCode'] == 404


def test_dispatch_answers_404_for_an_event_naming_no_resource() -> None:
    assert dispatch({}, {('/a', 'POST'): _echo})['statusCode'] == 404


def test_dispatch_names_the_error_of_a_route_it_does_not_hold() -> None:
    event = {'resource': '/b', 'httpMethod': 'POST'}
    assert json.loads(dispatch(event, {('/a', 'POST'): _echo})['body']) == {'error': 'Not found'}


def test_aws_client_asks_boto3_for_the_service(monkeypatch: pytest.MonkeyPatch) -> None:
    boto3 = SimpleNamespace(client=lambda service: f"a {service} client")
    monkeypatch.setattr(lambda_http, "boto3", boto3)
    monkeypatch.setattr(lambda_http, "_clients", {})
    assert aws_client("sqs") == "a sqs client"


def test_aws_client_keeps_the_client_it_made(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lambda_http, "boto3", SimpleNamespace(client=lambda service: object()))
    monkeypatch.setattr(lambda_http, "_clients", {})
    assert aws_client("sqs") is aws_client("sqs")


def test_aws_client_makes_a_client_per_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lambda_http, "boto3", SimpleNamespace(client=lambda service: object()))
    monkeypatch.setattr(lambda_http, "_clients", {})
    assert aws_client("sqs") is not aws_client("s3")
