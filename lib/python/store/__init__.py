from typing import Any, Dict, List, Optional

from lambda_http import aws_client

COUNTER = '#'


def partition(table: str, key: str, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
    condition = 'PK = :pk'
    values = {':pk': {'S': key}}
    if prefix is not None:
        condition += ' AND begins_with(SK, :prefix)'
        values[':prefix'] = {'S': prefix}
    answer = aws_client('dynamodb').query(
        TableName=table,
        KeyConditionExpression=condition,
        ExpressionAttributeValues=values,
    )
    items: List[Dict[str, Any]] = answer['Items']
    return items


def members(table: str, collection: str) -> List[Dict[str, Any]]:
    return [item for item in partition(table, collection) if item['SK']['S'] != COUNTER]


def member(table: str, collection: str, member_id: str) -> Optional[Dict[str, Any]]:
    answer = aws_client('dynamodb').get_item(
        TableName=table,
        Key={'PK': {'S': collection}, 'SK': {'S': member_id}},
    )
    item: Optional[Dict[str, Any]] = answer.get('Item')
    return item
