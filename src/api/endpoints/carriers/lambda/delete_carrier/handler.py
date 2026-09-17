import os
from typing import Any, Dict

from botocore.exceptions import ClientError

from carriers import COLLECTION, MISSING, logger, requested
from lambda_http import dispatch, error_response, no_content
from store import remove


def _delete(event: Dict[str, Any]) -> Dict[str, Any]:
    carrier_id = requested(event)
    if carrier_id is None:
        return error_response(404, MISSING)
    try:
        removed = remove(os.environ['STORE_TABLE'], COLLECTION, carrier_id)
    except ClientError as error:
        logger.error('Error deleting carrier %s: %s', carrier_id, error)
        return error_response(500, 'Failed to delete the carrier')
    if not removed:
        return error_response(404, MISSING)
    return no_content()


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(f'/{COLLECTION}/{{id}}', 'DELETE'): _delete})
