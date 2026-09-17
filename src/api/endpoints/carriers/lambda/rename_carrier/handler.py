import os
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError

from carriers import BODY, COLLECTION, MISSING, carrier, logger, named, requested, staled
from lambda_http import dispatch, error_response, json_response
from store import conditioned


def _rename(carrier_id: str, name: str) -> Optional[Dict[str, Any]]:
    key = {'PK': {'S': COLLECTION}, 'SK': {'S': carrier_id}}
    return conditioned(
        'update_item', os.environ['STORE_TABLE'], key,
        UpdateExpression='SET #name = :name',
        ExpressionAttributeNames={'#name': 'name'},
        ExpressionAttributeValues={':name': {'S': name}},
        ReturnValues='ALL_NEW',
    )


def _update(event: Dict[str, Any]) -> Dict[str, Any]:
    name = named(event)
    if name is None:
        return error_response(400, BODY)
    carrier_id = requested(event)
    if carrier_id is None:
        return error_response(404, MISSING)
    try:
        item = _rename(carrier_id, name)
    except ClientError as error:
        logger.error('Error renaming carrier %s: %s', carrier_id, error)
        return error_response(500, 'Failed to update the carrier')
    if item is None:
        return error_response(404, MISSING)
    staled(carrier_id)
    return json_response(200, carrier(item))


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(f'/{COLLECTION}/{{id}}', 'PUT'): _update})
