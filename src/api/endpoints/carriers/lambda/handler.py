import logging
import os
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from lambda_http import aws_client, dispatch, json_response, parse_object

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COLLECTION = 'carriers'
COUNTER = '#'
BODY = 'The body must be exactly {"name"}'


def _members(collection: str) -> List[Dict[str, Any]]:
    answer = aws_client('dynamodb').query(
        TableName=os.environ['STORE_TABLE'],
        KeyConditionExpression='PK = :pk',
        ExpressionAttributeValues={':pk': {'S': collection}},
    )
    return [item for item in answer['Items'] if item['SK']['S'] != COUNTER]


def _carrier(item: Dict[str, Any]) -> Dict[str, Any]:
    return {'id': int(item['SK']['S']), 'name': item['name']['S']}


def _list(_event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        members = _members(COLLECTION)
    except ClientError as error:
        logger.error('Error reading the carriers: %s', error)
        return json_response(500, {'error': 'Failed to read the carriers'})
    return json_response(200, sorted(map(_carrier, members), key=lambda carrier: carrier['id']))


def _name(event: Dict[str, Any]) -> Optional[str]:
    body = parse_object(event)
    if body is None or set(body) != {'name'}:
        return None
    name = body['name']
    return name if isinstance(name, str) and name else None


def _next_id(collection: str) -> int:
    answer = aws_client('dynamodb').update_item(
        TableName=os.environ['STORE_TABLE'],
        Key={'PK': {'S': collection}, 'SK': {'S': COUNTER}},
        UpdateExpression='SET #next = if_not_exists(#next, :one) + :one',
        ExpressionAttributeNames={'#next': 'next'},
        ExpressionAttributeValues={':one': {'N': '1'}},
        ReturnValues='UPDATED_NEW',
    )
    return int(answer['Attributes']['next']['N']) - 1


def _put(carrier_id: int, name: str) -> None:
    aws_client('dynamodb').put_item(
        TableName=os.environ['STORE_TABLE'],
        Item={
            'PK': {'S': COLLECTION},
            'SK': {'S': str(carrier_id)},
            'name': {'S': name},
            'next_pop': {'N': '1'},
            'next_fiber_segment': {'N': '1'},
        },
    )


def _create(event: Dict[str, Any]) -> Dict[str, Any]:
    name = _name(event)
    if name is None:
        return json_response(400, {'error': BODY})
    try:
        carrier_id = _next_id(COLLECTION)
        _put(carrier_id, name)
    except ClientError as error:
        logger.error('Error creating the carrier: %s', error)
        return json_response(500, {'error': 'Failed to create the carrier'})
    response = json_response(201, {'id': carrier_id, 'name': name})
    response['headers']['Location'] = f'/{COLLECTION}/{carrier_id}'
    return response


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {('/carriers', 'GET'): _list, ('/carriers', 'POST'): _create})
