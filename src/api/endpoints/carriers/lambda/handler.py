import logging
import os
from typing import Any, Dict, List

from botocore.exceptions import ClientError

from lambda_http import aws_client, dispatch, json_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COLLECTION = 'carriers'
COUNTER = '#'


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


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {('/carriers', 'GET'): _list})
