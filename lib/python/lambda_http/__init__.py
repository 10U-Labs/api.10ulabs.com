import base64
import json
from typing import Any, Callable, Dict, Mapping, Tuple

Handler = Callable[[Dict[str, Any]], Dict[str, Any]]
Route = Tuple[str, str]


def json_response(status_code: int, body: Any) -> Dict[str, Any]:
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body)
    }


def parse_body(event: Dict[str, Any]) -> Any:
    body = event.get('body') or ''
    if event.get('isBase64Encoded'):
        body = base64.b64decode(body).decode('utf-8')
    return json.loads(body) if body else {}


def dispatch(event: Dict[str, Any], routes: Mapping[Route, Handler]) -> Dict[str, Any]:
    handler = routes.get((event.get('resource', ''), event.get('httpMethod', '')))
    if handler is None:
        return json_response(404, {'error': 'Not found'})
    return handler(event)
