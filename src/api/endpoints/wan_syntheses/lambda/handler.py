import logging
import os
from typing import Any, Dict

from botocore.exceptions import ClientError

from lambda_http import dispatch, error_response, json_response, path_id
from store import member, members, plain

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COLLECTION = 'wan-syntheses'
KEY = ('PK', 'SK')
MISSING = 'No such wan synthesis'


def _synthesis(item: Dict[str, Any]) -> Dict[str, Any]:
    return {'id': int(item['SK']['S']), 'label': item['label']['S']}


def _list(_event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        syntheses = members(os.environ['STORE_TABLE'], COLLECTION)
    except ClientError as error:
        logger.error('Error reading the wan syntheses: %s', error)
        return error_response(500, 'Failed to read the wan syntheses')
    return json_response(200, sorted(map(_synthesis, syntheses), key=lambda one: one['id']))


def _record(item: Dict[str, Any]) -> Dict[str, Any]:
    held = {field: plain(value) for field, value in item.items() if field not in KEY}
    return {'id': int(item['SK']['S']), **held}


def _read(event: Dict[str, Any]) -> Dict[str, Any]:
    synthesis_id = path_id(event, 'synthesis')
    if synthesis_id is None:
        return error_response(404, MISSING)
    try:
        item = member(os.environ['STORE_TABLE'], COLLECTION, synthesis_id)
    except ClientError as error:
        logger.error('Error reading wan synthesis %s: %s', synthesis_id, error)
        return error_response(500, 'Failed to read the wan synthesis')
    if item is None:
        return error_response(404, MISSING)
    return json_response(200, _record(item))


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {
        (f'/{COLLECTION}', 'GET'): _list,
        (f'/{COLLECTION}/{{synthesis}}', 'GET'): _read,
    })
