from typing import Any, Dict

from lambda_http import dispatch, json_response

HEALTH = {
    'status': 'healthy',
    'service': '10U Labs API',
    'version': '1.0.0'
}


def _health(_event: Dict[str, Any]) -> Dict[str, Any]:
    return json_response(200, HEALTH)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {('/health', 'GET'): _health})
