import logging
import os
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError

from lambda_http import (
    created, dispatch, error_response, has_numbers, has_strings, json_response, no_content,
    parse_valid, path_id,
)
from store import conditional, delete, member, members, next_id, put, sort_id

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
        'id': sort_id(item),
        **{field: item[field]['S'] for field in WORDED},
        **{field: float(item[field]['N']) for field in COORDINATES},
    }


def _list(_event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        regions = members(os.environ['STORE_TABLE'], COLLECTION)
    except ClientError as error:
        logger.error('Error reading the hyperscale cloud service provider regions: %s', error)
        return error_response(500, 'Failed to read the hyperscale cloud service provider regions')
    return json_response(200, sorted(map(_region, regions), key=lambda region: region['id']))


def _read(event: Dict[str, Any]) -> Dict[str, Any]:
    region_id = path_id(event, 'region')
    if region_id is None:
        return error_response(404, MISSING)
    try:
        item = member(os.environ['STORE_TABLE'], COLLECTION, region_id)
    except ClientError as error:
        logger.error('Error reading region %s: %s', region_id, error)
        return error_response(500, 'Failed to read the hyperscale cloud service provider region')
    if item is None:
        return error_response(404, MISSING)
    return json_response(200, _region(item))


def _region_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return parse_valid(
        event, WORDED + COORDINATES,
        lambda body: has_strings(body, WORDED, NAMED) and has_numbers(body, COORDINATES),
    )


def _attributes(body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **{field: {'S': body[field]} for field in WORDED},
        **{field: {'N': str(body[field])} for field in COORDINATES},
    }


def _create(event: Dict[str, Any]) -> Dict[str, Any]:
    body = _region_body(event)
    if body is None:
        return error_response(400, REGION_BODY)
    table = os.environ['STORE_TABLE']
    try:
        region_id = next_id(table, COLLECTION)
        item = put(table, COLLECTION, str(region_id), _attributes(body))
    except ClientError as error:
        logger.error('Error creating the hyperscale cloud service provider region: %s', error)
        return error_response(500, 'Failed to create the hyperscale cloud service provider region')
    return created(f'/{COLLECTION}/{region_id}', _region(item))


def _update(event: Dict[str, Any]) -> Dict[str, Any]:
    body = _region_body(event)
    if body is None:
        return error_response(400, REGION_BODY)
    region_id = path_id(event, 'region')
    if region_id is None:
        return error_response(404, MISSING)
    try:
        item = put(
            os.environ['STORE_TABLE'], COLLECTION, region_id, _attributes(body),
            ConditionExpression='attribute_exists(PK)',
        )
    except ClientError as error:
        if conditional(error):
            return error_response(404, MISSING)
        logger.error('Error updating region %s: %s', region_id, error)
        return error_response(500, 'Failed to update the hyperscale cloud service provider region')
    return json_response(200, _region(item))


def _delete(event: Dict[str, Any]) -> Dict[str, Any]:
    region_id = path_id(event, 'region')
    if region_id is None:
        return error_response(404, MISSING)
    try:
        removed = delete(os.environ['STORE_TABLE'], COLLECTION, region_id)
    except ClientError as error:
        logger.error('Error deleting region %s: %s', region_id, error)
        return error_response(500, 'Failed to delete the hyperscale cloud service provider region')
    if removed is None:
        return error_response(404, MISSING)
    return no_content()


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {
        (f'/{COLLECTION}', 'GET'): _list,
        (f'/{COLLECTION}', 'POST'): _create,
        (f'/{COLLECTION}/{{region}}', 'GET'): _read,
        (f'/{COLLECTION}/{{region}}', 'PUT'): _update,
        (f'/{COLLECTION}/{{region}}', 'DELETE'): _delete,
    })
