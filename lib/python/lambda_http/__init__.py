import base64
import json
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Tuple

import boto3

Handler = Callable[[Dict[str, Any]], Dict[str, Any]]
Route = Tuple[str, str]

_clients: Dict[str, Any] = {}


def aws_client(service: str) -> Any:
    if service not in _clients:
        _clients[service] = boto3.client(service)
    return _clients[service]


def json_response(status_code: int, body: Any) -> Dict[str, Any]:
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body)
    }


def no_content() -> Dict[str, Any]:
    return {'statusCode': 204, 'headers': {}, 'body': ''}


def error_response(status_code: int, message: str) -> Dict[str, Any]:
    return json_response(status_code, {'error': message})


def created(location: str, body: Any) -> Dict[str, Any]:
    response = json_response(201, body)
    response['headers']['Location'] = location
    return response


def parse_body(event: Dict[str, Any]) -> Any:
    body = event.get('body') or ''
    if event.get('isBase64Encoded'):
        body = base64.b64decode(body).decode('utf-8')
    return json.loads(body) if body else {}


def parse_object(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        body = parse_body(event)
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


def parse_fields(event: Dict[str, Any], fields: Iterable[str]) -> Optional[Dict[str, Any]]:
    body = parse_object(event)
    return body if body is not None and set(body) == set(fields) else None


Valid = Callable[[Dict[str, Any]], bool]


def parse_valid(
    event: Dict[str, Any], fields: Iterable[str], valid: Valid
) -> Optional[Dict[str, Any]]:
    body = parse_fields(event, fields)
    return body if body is not None and valid(body) else None


def has_strings(body: Dict[str, Any], fields: Iterable[str], named: Iterable[str] = ()) -> bool:
    worded = all(isinstance(body[field], str) for field in fields)
    return worded and all(body[field] for field in named)


def has_numbers(body: Dict[str, Any], fields: Iterable[str]) -> bool:
    return all(
        isinstance(body[field], (int, float)) and not isinstance(body[field], bool)
        for field in fields
    )


def path_id(event: Dict[str, Any], name: str) -> Optional[str]:
    member_id = str((event.get('pathParameters') or {}).get(name) or '')
    return member_id if member_id.isdigit() else None


def dispatch(event: Dict[str, Any], routes: Mapping[Route, Handler]) -> Dict[str, Any]:
    handler = routes.get((event.get('resource', ''), event.get('httpMethod', '')))
    if handler is None:
        return json_response(404, {'error': 'Not found'})
    return handler(event)
