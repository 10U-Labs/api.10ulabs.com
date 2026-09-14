import logging
import os
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError

from lambda_http import dispatch, error_response, json_response, path_id
from store import member, members, partition, plain, sort_id

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COLLECTION = 'wan-syntheses'
KEY = ('PK', 'SK')
MISSING = 'No such wan synthesis'
NO_WAN = 'The synthesis has no wan'


def _synthesis(item: Dict[str, Any]) -> Dict[str, Any]:
    return {'id': sort_id(item), 'label': item['label']['S']}


def _list(_event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        syntheses = members(os.environ['STORE_TABLE'], COLLECTION)
    except ClientError as error:
        logger.error('Error reading the wan syntheses: %s', error)
        return error_response(500, 'Failed to read the wan syntheses')
    return json_response(200, sorted(map(_synthesis, syntheses), key=lambda one: one['id']))


def _record(item: Dict[str, Any]) -> Dict[str, Any]:
    held = {field: plain(value) for field, value in item.items() if field not in KEY}
    return {'id': sort_id(item), **held}


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


def _has_wan(record: Optional[Dict[str, Any]]) -> bool:
    return record is not None and record['status']['S'] == 'success'


def _list_under(event: Dict[str, Any], prefix: str, failure: str) -> Dict[str, Any]:
    synthesis_id = path_id(event, 'synthesis')
    if synthesis_id is None:
        return error_response(404, MISSING)
    table = os.environ['STORE_TABLE']
    try:
        record = member(table, COLLECTION, synthesis_id)
        under = f'{COLLECTION}/{synthesis_id}'
        items = partition(table, under, f'{prefix}/') if _has_wan(record) else []
    except ClientError as error:
        logger.error('Error reading the %s of wan synthesis %s: %s', prefix, synthesis_id, error)
        return error_response(500, failure)
    if record is None:
        return error_response(404, MISSING)
    if not _has_wan(record):
        return error_response(404, NO_WAN)
    return json_response(200, sorted(map(_record, items), key=lambda one: one['id']))


def _list_wan_pops(event: Dict[str, Any]) -> Dict[str, Any]:
    return _list_under(event, 'wan-pops', 'Failed to read the wan pops')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {
        (f'/{COLLECTION}', 'GET'): _list,
        (f'/{COLLECTION}/{{synthesis}}', 'GET'): _read,
        (f'/{COLLECTION}/{{synthesis}}/wan-pops', 'GET'): _list_wan_pops,
    })
