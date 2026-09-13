import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from lambda_http import aws_client, dispatch, json_response, parse_object

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ISO8601 = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
EVENTS_MAXIMUM = 25
WRITE_ATTEMPTS = 5
CORS_HEADERS = {'Access-Control-Allow-Origin': '*'}


def _error(status_code: int, message: str, details: Optional[str] = None) -> Dict[str, Any]:
    body: Dict[str, Any] = {'success': False, 'error': message}
    if details:
        body['details'] = details
    return json_response(status_code, body)


def _request_error(body: Dict[str, Any]) -> Optional[str]:
    for field in ('device_id', 'events'):
        if field not in body:
            return f'Missing required field: {field}'
    if not isinstance(body['device_id'], str):
        return 'device_id must be a string'
    if not isinstance(body['events'], list):
        return 'events must be an array'
    if not body['events']:
        return 'events array cannot be empty'
    if len(body['events']) > EVENTS_MAXIMUM:
        return f'events array cannot exceed {EVENTS_MAXIMUM} items'
    return None


def _event_error(event: Any) -> Optional[str]:
    if not isinstance(event, dict):
        return 'event must be an object'
    for field in ('event_type', 'timestamp'):
        if field not in event:
            return f'Missing required field: {field}'
        if not isinstance(event[field], str):
            return f'{field} must be a string'
    if not ISO8601.match(event['timestamp']):
        return 'timestamp must be in ISO8601 format'
    return None


def _events_error(events: List[Any]) -> Optional[str]:
    errors = [f'Event {index}: {error}' for index, event in enumerate(events)
              if (error := _event_error(event))]
    return '; '.join(errors) or None


def _item(session_id: str, body: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
    item = {
        'session_id': {'S': session_id},
        'timestamp': {'S': event['timestamp']},
        'device_id': {'S': body['device_id']},
        'event_type': {'S': event['event_type']},
        'event_data': {'S': json.dumps(event)},
    }
    if body.get('session_context'):
        item['session_context'] = {'S': json.dumps(body['session_context'])}
    return item


def _write(items: List[Dict[str, Any]]) -> None:
    table = os.environ['SESSION_EVENTS_TABLE']
    pending = {table: [{'PutRequest': {'Item': item}} for item in items]}
    for attempt in range(WRITE_ATTEMPTS):
        written = aws_client('dynamodb').batch_write_item(RequestItems=pending)
        pending = written.get('UnprocessedItems') or {}
        if not pending:
            return
        time.sleep(0.1 * 2 ** attempt)
    raise ClientError({'Error': {'Code': 'UnprocessedItems', 'Message': 'events left unwritten'}},
                      'BatchWriteItem')


def _record(event: Dict[str, Any]) -> Dict[str, Any]:
    session_id = (event.get('pathParameters') or {}).get('session_id') or ''
    if not session_id:
        return _error(400, 'Invalid path: missing session_id')
    body = parse_object(event)
    if body is None:
        return _error(400, 'Invalid JSON')
    request_error = _request_error(body)
    if request_error:
        return _error(400, request_error)
    events_error = _events_error(body['events'])
    if events_error:
        return _error(400, 'Invalid events', events_error)
    try:
        _write([_item(session_id, body, item) for item in body['events']])
    except ClientError as error:
        logger.error('Error recording session events: %s', error)
        return _error(500, 'Failed to record the events')
    return json_response(200, {'success': True, 'events_saved': len(body['events'])})


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    response = dispatch(event, {('/v1/sessions/{session_id}/events', 'POST'): _record})
    response['headers'].update(CORS_HEADERS)
    return response
