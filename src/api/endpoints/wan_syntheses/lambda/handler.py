import logging
import os
from typing import Any, Dict, NamedTuple, Optional

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


class Part(NamedTuple):
    prefix: str
    parameter: str
    missing: str


WAN_POPS = Part('wan-pops', 'wan-pop', 'No such wan pop')
BACKBONE_CIRCUITS = Part('backbone-circuits', 'backbone-circuit', 'No such backbone circuit')


def _has_wan(record: Optional[Dict[str, Any]]) -> bool:
    return record is not None and record['status']['S'] == 'success'


def _wan_refusal(record: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if record is None:
        return error_response(404, MISSING)
    return None if _has_wan(record) else error_response(404, NO_WAN)


def _list_under(event: Dict[str, Any], part: Part, failure: str) -> Dict[str, Any]:
    synthesis_id = path_id(event, 'synthesis')
    if synthesis_id is None:
        return error_response(404, MISSING)
    table = os.environ['STORE_TABLE']
    try:
        record = member(table, COLLECTION, synthesis_id)
        under = f'{COLLECTION}/{synthesis_id}'
        items = partition(table, under, f'{part.prefix}/') if _has_wan(record) else []
    except ClientError as error:
        logger.error('Error reading the %s of synthesis %s: %s', part.prefix, synthesis_id, error)
        return error_response(500, failure)
    refused = _wan_refusal(record)
    if refused is not None:
        return refused
    return json_response(200, sorted(map(_record, items), key=lambda one: one['id']))


def _read_under(event: Dict[str, Any], part: Part, failure: str) -> Dict[str, Any]:
    synthesis_id = path_id(event, 'synthesis')
    if synthesis_id is None:
        return error_response(404, MISSING)
    part_id = path_id(event, part.parameter)
    if part_id is None:
        return error_response(404, part.missing)
    table = os.environ['STORE_TABLE']
    try:
        record = member(table, COLLECTION, synthesis_id)
        under = f'{COLLECTION}/{synthesis_id}'
        item = member(table, under, f'{part.prefix}/{part_id}') if _has_wan(record) else None
    except ClientError as error:
        logger.error(
            'Error reading %s/%s of synthesis %s: %s', part.prefix, part_id, synthesis_id, error
        )
        return error_response(500, failure)
    refused = _wan_refusal(record)
    if refused is not None:
        return refused
    if item is None:
        return error_response(404, part.missing)
    return json_response(200, _record(item))


def _list_wan_pops(event: Dict[str, Any]) -> Dict[str, Any]:
    return _list_under(event, WAN_POPS, 'Failed to read the wan pops')


def _read_wan_pop(event: Dict[str, Any]) -> Dict[str, Any]:
    return _read_under(event, WAN_POPS, 'Failed to read the wan pop')


def _list_backbone_circuits(event: Dict[str, Any]) -> Dict[str, Any]:
    return _list_under(event, BACKBONE_CIRCUITS, 'Failed to read the backbone circuits')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {
        (f'/{COLLECTION}', 'GET'): _list,
        (f'/{COLLECTION}/{{synthesis}}', 'GET'): _read,
        (f'/{COLLECTION}/{{synthesis}}/wan-pops', 'GET'): _list_wan_pops,
        (f'/{COLLECTION}/{{synthesis}}/wan-pops/{{wan-pop}}', 'GET'): _read_wan_pop,
        (f'/{COLLECTION}/{{synthesis}}/backbone-circuits', 'GET'): _list_backbone_circuits,
    })
