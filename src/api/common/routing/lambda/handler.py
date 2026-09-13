import json
from typing import Any, Dict


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return {
        'statusCode': 404,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'error': 'Not Found',
            'message': 'The requested endpoint does not exist',
            'path': event.get('path', 'unknown')
        })
    }
