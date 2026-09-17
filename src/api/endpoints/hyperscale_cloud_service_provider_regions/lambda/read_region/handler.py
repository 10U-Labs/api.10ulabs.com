import os
from typing import Any, Dict

from botocore.exceptions import ClientError

from lambda_http import dispatch, error_response, json_response, path_id
from regions import COLLECTION, MEMBER, MISSING, logger, region
from store import member

FAILURE = 'Failed to read the hyperscale cloud service provider region'


def _read(event: Dict[str, Any]) -> Dict[str, Any]:
    region_id = path_id(event, 'id')
    if region_id is None:
        return error_response(404, MISSING)
    try:
        item = member(os.environ['STORE_TABLE'], COLLECTION, region_id)
    except ClientError as error:
        logger.error('Error reading region %s: %s', region_id, error)
        return error_response(500, FAILURE)
    if item is None:
        return error_response(404, MISSING)
    return json_response(200, region(item))


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(MEMBER, 'GET'): _read})
