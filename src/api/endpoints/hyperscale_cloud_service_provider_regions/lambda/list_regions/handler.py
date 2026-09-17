import os
from typing import Any, Dict

from botocore.exceptions import ClientError

from lambda_http import dispatch, error_response, json_response
from regions import COLLECTION, ROUTE, logger, region
from store import members

FAILURE = 'Failed to read the hyperscale cloud service provider regions'


def _list(_event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        regions = members(os.environ['STORE_TABLE'], COLLECTION)
    except ClientError as error:
        logger.error('Error reading the hyperscale cloud service provider regions: %s', error)
        return error_response(500, FAILURE)
    rows = sorted(map(region, regions), key=lambda one: one['id'])
    return json_response(200, rows)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(ROUTE, 'GET'): _list})
