import os
from typing import Any, Dict

from botocore.exceptions import ClientError

from lambda_http import dispatch, error_response, json_response, path_id
from store import member
from syntheses import COLLECTION, MISSING, logger, record


def _read(event: Dict[str, Any]) -> Dict[str, Any]:
    synthesis_id = path_id(event, 'id')
    if synthesis_id is None:
        return error_response(404, MISSING)
    try:
        item = member(os.environ['STORE_TABLE'], COLLECTION, synthesis_id)
    except ClientError as error:
        logger.error('Error reading wan synthesis %s: %s', synthesis_id, error)
        return error_response(500, 'Failed to read the wan synthesis')
    if item is None:
        return error_response(404, MISSING)
    return json_response(200, record(item))


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(f'/{COLLECTION}/{{id}}', 'GET'): _read})
