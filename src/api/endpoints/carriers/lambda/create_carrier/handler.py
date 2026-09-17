import os
from typing import Any, Dict

from botocore.exceptions import ClientError

from carriers import BODY, COLLECTION, logger, named, staled
from lambda_http import created, dispatch, error_response
from store import next_id, put


def _create(event: Dict[str, Any]) -> Dict[str, Any]:
    name = named(event)
    if name is None:
        return error_response(400, BODY)
    table = os.environ['STORE_TABLE']
    try:
        carrier_id = next_id(table, COLLECTION)
        put(table, COLLECTION, str(carrier_id), {
            'name': {'S': name}, 'next_pop': {'N': '1'}, 'next_fiber_segment': {'N': '1'},
        })
    except ClientError as error:
        logger.error('Error creating the carrier: %s', error)
        return error_response(500, 'Failed to create the carrier')
    staled(str(carrier_id))
    return created(f'/{COLLECTION}/{carrier_id}', {'id': carrier_id, 'name': name})


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(f'/{COLLECTION}', 'POST'): _create})
