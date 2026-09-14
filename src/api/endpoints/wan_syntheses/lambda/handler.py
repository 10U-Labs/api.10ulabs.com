import logging
import os
from typing import Any, Dict

from botocore.exceptions import ClientError

from lambda_http import dispatch, error_response, json_response
from store import members

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COLLECTION = 'wan-syntheses'


def _synthesis(item: Dict[str, Any]) -> Dict[str, Any]:
    return {'id': int(item['SK']['S']), 'label': item['label']['S']}


def _list(_event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        syntheses = members(os.environ['STORE_TABLE'], COLLECTION)
    except ClientError as error:
        logger.error('Error reading the wan syntheses: %s', error)
        return error_response(500, 'Failed to read the wan syntheses')
    return json_response(200, sorted(map(_synthesis, syntheses), key=lambda one: one['id']))


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {
        (f'/{COLLECTION}', 'GET'): _list,
    })
