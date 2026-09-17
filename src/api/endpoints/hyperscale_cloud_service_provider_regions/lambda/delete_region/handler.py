import os
from typing import Any, Dict

from botocore.exceptions import ClientError

from lambda_http import dispatch, error_response, no_content, path_id
from regions import COLLECTION, MEMBER, MISSING, logger, staled
from store import delete

FAILURE = 'Failed to delete the hyperscale cloud service provider region'


def _delete(event: Dict[str, Any]) -> Dict[str, Any]:
    region_id = path_id(event, 'id')
    if region_id is None:
        return error_response(404, MISSING)
    try:
        removed = delete(os.environ['STORE_TABLE'], COLLECTION, region_id)
    except ClientError as error:
        logger.error('Error deleting region %s: %s', region_id, error)
        return error_response(500, FAILURE)
    if removed is None:
        return error_response(404, MISSING)
    staled(region_id)
    return no_content()


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(MEMBER, 'DELETE'): _delete})
