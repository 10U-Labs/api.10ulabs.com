import json
import os
from typing import Any, Dict

HTML = 'text/html'


def _accepted(event: Dict[str, Any]) -> str:
    headers = event.get('headers') or {}
    return ' '.join(str(value) for name, value in headers.items() if name.lower() == 'accept')


def _page() -> Dict[str, Any]:
    return {
        'statusCode': 404,
        'headers': {'Content-Type': HTML},
        'body': os.environ['NOT_FOUND_PAGE'],
    }


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    if HTML in _accepted(event):
        return _page()
    return {
        'statusCode': 404,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'error': 'Not Found',
            'message': 'The requested endpoint does not exist',
            'path': event.get('path', 'unknown')
        })
    }
