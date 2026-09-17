import os
from typing import Any, Dict

from botocore.exceptions import ClientError

from carriers import COLLECTION, carrier, logger
from lambda_http import dispatch, error_response, json_response
from store import members


def _list(_event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        carriers = members(os.environ['STORE_TABLE'], COLLECTION)
    except ClientError as error:
        logger.error('Error reading the carriers: %s', error)
        return error_response(500, 'Failed to read the carriers')
    return json_response(200, sorted(map(carrier, carriers), key=lambda one: one['id']))


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(f'/{COLLECTION}', 'GET'): _list})
