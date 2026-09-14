import logging
import os
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError

from lambda_http import (
    created, dispatch, has_numbers, has_strings, json_response, parse_valid, path_id,
)
from store import member, members, next_id, put

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COLLECTION = 'hyperscale-cloud-service-provider-regions'
WORDED = ('name', 'municipality', 'state', 'country')
NAMED = ('name', 'municipality', 'country')
COORDINATES = ('latitude', 'longitude')
MISSING = 'No such hyperscale cloud service provider region'
REGION_BODY = (
    'The body must be exactly '
    '{"name", "municipality", "state", "country", "latitude", "longitude"}'
)


def _region(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': int(item['SK']['S']),
        **{field: item[field]['S'] for field in WORDED},
        **{field: float(item[field]['N']) for field in COORDINATES},
    }


def _list(_event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        regions = members(os.environ['STORE_TABLE'], COLLECTION)
    except ClientError as error:
        logger.error('Error reading the hyperscale cloud service provider regions: %s', error)
        return json_response(
            500, {'error': 'Failed to read the hyperscale cloud service provider regions'}
        )
    return json_response(200, sorted(map(_region, regions), key=lambda region: region['id']))


def _read(event: Dict[str, Any]) -> Dict[str, Any]:
    region_id = path_id(event, 'region')
    if region_id is None:
        return json_response(404, {'error': MISSING})
    try:
        item = member(os.environ['STORE_TABLE'], COLLECTION, region_id)
    except ClientError as error:
        logger.error('Error reading region %s: %s', region_id, error)
        return json_response(
            500, {'error': 'Failed to read the hyperscale cloud service provider region'}
        )
    if item is None:
        return json_response(404, {'error': MISSING})
    return json_response(200, _region(item))


def _region_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return parse_valid(
        event, WORDED + COORDINATES,
        lambda body: has_strings(body, WORDED, NAMED) and has_numbers(body, COORDINATES),
    )


def _create(event: Dict[str, Any]) -> Dict[str, Any]:
    body = _region_body(event)
    if body is None:
        return json_response(400, {'error': REGION_BODY})
    table = os.environ['STORE_TABLE']
    try:
        region_id = next_id(table, COLLECTION)
        item = put(table, COLLECTION, str(region_id), {
            **{field: {'S': body[field]} for field in WORDED},
            **{field: {'N': str(body[field])} for field in COORDINATES},
        })
    except ClientError as error:
        logger.error('Error creating the hyperscale cloud service provider region: %s', error)
        return json_response(
            500, {'error': 'Failed to create the hyperscale cloud service provider region'}
        )
    return created(f'/{COLLECTION}/{region_id}', _region(item))


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {
        (f'/{COLLECTION}', 'GET'): _list,
        (f'/{COLLECTION}', 'POST'): _create,
        (f'/{COLLECTION}/{{region}}', 'GET'): _read,
    })
