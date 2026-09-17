from typing import Any, Dict

from botocore.exceptions import ClientError

from carriers import COLLECTION, MISSING, carrier, held, logger, requested
from lambda_http import dispatch, error_response, json_response


def _read(event: Dict[str, Any]) -> Dict[str, Any]:
    carrier_id = requested(event)
    if carrier_id is None:
        return error_response(404, MISSING)
    try:
        item = held(COLLECTION, carrier_id)
    except ClientError as error:
        logger.error('Error reading carrier %s: %s', carrier_id, error)
        return error_response(500, 'Failed to read the carrier')
    return json_response(200, carrier(item)) if item else error_response(404, MISSING)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(f'/{COLLECTION}/{{id}}', 'GET'): _read})
