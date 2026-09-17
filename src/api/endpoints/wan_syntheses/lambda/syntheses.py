import logging
import os
from typing import Any, Dict, NamedTuple, Optional

from botocore.exceptions import ClientError

from lambda_http import error_response, json_response, path_id
from store import member, partition, plain, sort_id

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COLLECTION = 'wan-syntheses'
KEY = ('PK', 'SK')
MISSING = 'No such wan synthesis'
NO_WAN = 'The synthesis has no wan'


def synthesis(item: Dict[str, Any]) -> Dict[str, Any]:
    return {'id': sort_id(item), 'label': item['label']['S']}


def record(item: Dict[str, Any]) -> Dict[str, Any]:
    fields = {field: plain(value) for field, value in item.items() if field not in KEY}
    return {'id': sort_id(item), **fields}


class Part(NamedTuple):
    prefix: str
    parameter: str
    missing: str
    given: bool = False


WAN_POPS = Part('wan-pops', 'wan_pop_id', 'No such wan pop')
BACKBONE_CIRCUITS = Part('backbone-circuits', 'backbone_circuit_id', 'No such backbone circuit')
HOMING_CIRCUITS = Part('homing-circuits', 'homing_circuit_id', 'No such homing circuit')
FIBER_SEGMENTS = Part('fiber-segments', 'fiber_segment_id', 'No such fiber segment')
SITES = Part('sites', 'site_id', 'No such site', given=True)
REGIONS = Part(
    'hyperscale-cloud-service-provider-regions', 'region_id',
    'No such hyperscale cloud service provider region', given=True,
)
OFF_NET = Part('off-net', 'off_net_pop_id', 'No such off-net pop', given=True)
FORCED_WAN_POPS = Part('forced-wan-pops', 'forced_wan_pop_id', 'No such forced wan pop', given=True)
FORCED_CIRCUITS = Part('forced-circuits', 'forced_circuit_id', 'No such forced circuit', given=True)
FORCED_HOMES = Part('forced-homes', 'forced_home_id', 'No such forced home', given=True)
PROHIBITED_WAN_POPS = Part(
    'prohibited-wan-pops', 'prohibited_wan_pop_id', 'No such prohibited wan pop', given=True
)
PROHIBITED_CIRCUITS = Part(
    'prohibited-circuits', 'prohibited_circuit_id', 'No such prohibited circuit', given=True
)
DEGREE_EXEMPT_WAN_POPS = Part(
    'degree-exempt-wan-pops', 'degree_exempt_wan_pop_id', 'No such degree-exempt wan pop',
    given=True,
)


def listed(part: Part) -> str:
    return f'/{COLLECTION}/{{id}}/{part.prefix}'


def one(part: Part) -> str:
    return f'{listed(part)}/{{{part.parameter}}}'


def held(stored: Optional[Dict[str, Any]], part: Part) -> bool:
    return stored is not None and (part.given or stored['status']['S'] == 'success')


def refusal(stored: Optional[Dict[str, Any]], part: Part) -> Optional[Dict[str, Any]]:
    if stored is None:
        return error_response(404, MISSING)
    return None if held(stored, part) else error_response(404, NO_WAN)


def list_under(event: Dict[str, Any], part: Part, failure: str) -> Dict[str, Any]:
    synthesis_id = path_id(event, 'id')
    if synthesis_id is None:
        return error_response(404, MISSING)
    table = os.environ['STORE_TABLE']
    try:
        stored = member(table, COLLECTION, synthesis_id)
        under = f'{COLLECTION}/{synthesis_id}'
        items = partition(table, under, f'{part.prefix}/') if held(stored, part) else []
    except ClientError as error:
        logger.error('Error reading the %s of synthesis %s: %s', part.prefix, synthesis_id, error)
        return error_response(500, failure)
    refused = refusal(stored, part)
    if refused is not None:
        return refused
    return json_response(200, sorted(map(record, items), key=lambda row: row['id']))


def read_under(event: Dict[str, Any], part: Part, failure: str) -> Dict[str, Any]:
    synthesis_id = path_id(event, 'id')
    if synthesis_id is None:
        return error_response(404, MISSING)
    part_id = path_id(event, part.parameter)
    if part_id is None:
        return error_response(404, part.missing)
    table = os.environ['STORE_TABLE']
    try:
        stored = member(table, COLLECTION, synthesis_id)
        under = f'{COLLECTION}/{synthesis_id}'
        item = member(table, under, f'{part.prefix}/{part_id}') if held(stored, part) else None
    except ClientError as error:
        logger.error(
            'Error reading %s/%s of synthesis %s: %s', part.prefix, part_id, synthesis_id, error
        )
        return error_response(500, failure)
    refused = refusal(stored, part)
    if refused is not None:
        return refused
    if item is None:
        return error_response(404, part.missing)
    return json_response(200, record(item))
