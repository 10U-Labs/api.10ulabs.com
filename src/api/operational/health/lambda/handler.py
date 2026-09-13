import json
from typing import Any, Dict

HEALTH = {
    'status': 'healthy',
    'service': '10U Labs API',
    'version': '1.0.0'
}


def _json_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(body)
    }


def _is_health(event: Dict[str, Any]) -> bool:
    return event.get('path') == '/health' and event.get('httpMethod') == 'GET'


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    if _is_health(event):
        return _json_response(200, HEALTH)
    return _json_response(404, {'error': 'Not found'})
