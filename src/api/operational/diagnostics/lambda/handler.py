from typing import Any, Dict

from lambda_http import dispatch, json_response, parse_body


def _echo(event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        body = parse_body(event)
    except ValueError:
        return json_response(400, {'error': 'Invalid JSON'})
    request_id = event.get('requestContext', {}).get('requestId', 'N/A')
    return json_response(200, {'echo': body, 'received_at': request_id})


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {('/diagnostics/echo', 'POST'): _echo})
