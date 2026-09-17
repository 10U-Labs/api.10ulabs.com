import os
from typing import Any, Dict

from botocore.exceptions import ClientError

from lambda_http import dispatch, error_response, json_response, path_id
from regions import (
    COLLECTION, MEMBER, MISSING, REGION_BODY, attributes, logger, region, region_body,
)
from store import conditional, put

FAILURE = 'Failed to update the hyperscale cloud service provider region'


def _correct(event: Dict[str, Any]) -> Dict[str, Any]:
    body = region_body(event)
    if body is None:
        return error_response(400, REGION_BODY)
    region_id = path_id(event, 'id')
    if region_id is None:
        return error_response(404, MISSING)
    try:
        item = put(
            os.environ['STORE_TABLE'], COLLECTION, region_id, attributes(body),
            ConditionExpression='attribute_exists(PK)',
        )
    except ClientError as error:
        if conditional(error):
            return error_response(404, MISSING)
        logger.error('Error updating region %s: %s', region_id, error)
        return error_response(500, FAILURE)
    return json_response(200, region(item))


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(MEMBER, 'PUT'): _correct})
