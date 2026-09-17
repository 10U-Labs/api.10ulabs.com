import os
from typing import Any, Dict

from botocore.exceptions import ClientError

from lambda_http import created, dispatch, error_response
from regions import COLLECTION, REGION_BODY, ROUTE, attributes, logger, region, region_body
from store import next_id, put

FAILURE = 'Failed to create the hyperscale cloud service provider region'


def _create(event: Dict[str, Any]) -> Dict[str, Any]:
    body = region_body(event)
    if body is None:
        return error_response(400, REGION_BODY)
    table = os.environ['STORE_TABLE']
    try:
        region_id = next_id(table, COLLECTION)
        item = put(table, COLLECTION, str(region_id), attributes(body))
    except ClientError as error:
        logger.error('Error creating the hyperscale cloud service provider region: %s', error)
        return error_response(500, FAILURE)
    return created(f'{ROUTE}/{region_id}', region(item))


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(ROUTE, 'POST'): _create})
