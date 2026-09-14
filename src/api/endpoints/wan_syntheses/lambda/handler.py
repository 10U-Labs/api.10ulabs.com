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
    given: bool = False


WAN_POPS = Part('wan-pops', 'wan-pop', 'No such wan pop')
BACKBONE_CIRCUITS = Part('backbone-circuits', 'backbone-circuit', 'No such backbone circuit')
HOMING_CIRCUITS = Part('homing-circuits', 'homing-circuit', 'No such homing circuit')
FIBER_SEGMENTS = Part('fiber-segments', 'fiber-segment', 'No such fiber segment')
SITES = Part('sites', 'site', 'No such site', given=True)
REGIONS = Part(
    'hyperscale-cloud-service-provider-regions', 'region',
    'No such hyperscale cloud service provider region', given=True,
)
OFF_NET = Part('off-net', 'off-net-pop', 'No such off-net pop', given=True)
FORCED_WAN_POPS = Part('forced-wan-pops', 'forced-wan-pop', 'No such forced wan pop', given=True)
FORCED_CIRCUITS = Part('forced-circuits', 'forced-circuit', 'No such forced circuit', given=True)
FORCED_HOMES = Part('forced-homes', 'forced-home', 'No such forced home', given=True)
PROHIBITED_WAN_POPS = Part(
    'prohibited-wan-pops', 'prohibited-wan-pop', 'No such prohibited wan pop', given=True
)


def _listed(part: Part) -> str:
    return f'/{COLLECTION}/{{synthesis}}/{part.prefix}'


def _one(part: Part) -> str:
    return f'{_listed(part)}/{{{part.parameter}}}'


def _held(record: Optional[Dict[str, Any]], part: Part) -> bool:
    return record is not None and (part.given or record['status']['S'] == 'success')


def _refusal(record: Optional[Dict[str, Any]], part: Part) -> Optional[Dict[str, Any]]:
    if record is None:
        return error_response(404, MISSING)
    return None if _held(record, part) else error_response(404, NO_WAN)


def _list_under(event: Dict[str, Any], part: Part, failure: str) -> Dict[str, Any]:
    synthesis_id = path_id(event, 'synthesis')
    if synthesis_id is None:
        return error_response(404, MISSING)
    table = os.environ['STORE_TABLE']
    try:
        record = member(table, COLLECTION, synthesis_id)
        under = f'{COLLECTION}/{synthesis_id}'
        items = partition(table, under, f'{part.prefix}/') if _held(record, part) else []
    except ClientError as error:
        logger.error('Error reading the %s of synthesis %s: %s', part.prefix, synthesis_id, error)
        return error_response(500, failure)
    refused = _refusal(record, part)
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
        item = member(table, under, f'{part.prefix}/{part_id}') if _held(record, part) else None
    except ClientError as error:
        logger.error(
            'Error reading %s/%s of synthesis %s: %s', part.prefix, part_id, synthesis_id, error
        )
        return error_response(500, failure)
    refused = _refusal(record, part)
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


def _list_homing_circuits(event: Dict[str, Any]) -> Dict[str, Any]:
    return _list_under(event, HOMING_CIRCUITS, 'Failed to read the homing circuits')


def _list_fiber_segments(event: Dict[str, Any]) -> Dict[str, Any]:
    return _list_under(event, FIBER_SEGMENTS, 'Failed to read the fiber segments')


def _list_sites(event: Dict[str, Any]) -> Dict[str, Any]:
    return _list_under(event, SITES, 'Failed to read the sites')


def _read_site(event: Dict[str, Any]) -> Dict[str, Any]:
    return _read_under(event, SITES, 'Failed to read the site')


def _list_regions(event: Dict[str, Any]) -> Dict[str, Any]:
    return _list_under(
        event, REGIONS, 'Failed to read the hyperscale cloud service provider regions'
    )


def _read_region(event: Dict[str, Any]) -> Dict[str, Any]:
    return _read_under(
        event, REGIONS, 'Failed to read the hyperscale cloud service provider region'
    )


def _list_off_net(event: Dict[str, Any]) -> Dict[str, Any]:
    return _list_under(event, OFF_NET, 'Failed to read the off-net pops')


def _list_forced_wan_pops(event: Dict[str, Any]) -> Dict[str, Any]:
    return _list_under(event, FORCED_WAN_POPS, 'Failed to read the forced wan pops')


def _list_forced_circuits(event: Dict[str, Any]) -> Dict[str, Any]:
    return _list_under(event, FORCED_CIRCUITS, 'Failed to read the forced circuits')


def _list_forced_homes(event: Dict[str, Any]) -> Dict[str, Any]:
    return _list_under(event, FORCED_HOMES, 'Failed to read the forced homes')


def _list_prohibited_wan_pops(event: Dict[str, Any]) -> Dict[str, Any]:
    return _list_under(event, PROHIBITED_WAN_POPS, 'Failed to read the prohibited wan pops')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {
        (f'/{COLLECTION}', 'GET'): _list,
        (f'/{COLLECTION}/{{synthesis}}', 'GET'): _read,
        (_listed(WAN_POPS), 'GET'): _list_wan_pops,
        (_one(WAN_POPS), 'GET'): _read_wan_pop,
        (_listed(BACKBONE_CIRCUITS), 'GET'): _list_backbone_circuits,
        (_listed(HOMING_CIRCUITS), 'GET'): _list_homing_circuits,
        (_listed(FIBER_SEGMENTS), 'GET'): _list_fiber_segments,
        (_listed(SITES), 'GET'): _list_sites,
        (_one(SITES), 'GET'): _read_site,
        (_listed(REGIONS), 'GET'): _list_regions,
        (_one(REGIONS), 'GET'): _read_region,
        (_listed(OFF_NET), 'GET'): _list_off_net,
        (_listed(FORCED_WAN_POPS), 'GET'): _list_forced_wan_pops,
        (_listed(FORCED_CIRCUITS), 'GET'): _list_forced_circuits,
        (_listed(FORCED_HOMES), 'GET'): _list_forced_homes,
        (_listed(PROHIBITED_WAN_POPS), 'GET'): _list_prohibited_wan_pops,
    })
