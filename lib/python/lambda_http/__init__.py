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


def dispatch(event: Dict[str, Any], routes: Mapping[Route, Handler]) -> Dict[str, Any]:
    handler = routes.get((event.get('resource', ''), event.get('httpMethod', '')))
    if handler is None:
        return json_response(404, {'error': 'Not found'})
    return handler(event)
