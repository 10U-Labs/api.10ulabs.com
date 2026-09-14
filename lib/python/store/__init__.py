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


def advance(table: str, key: Dict[str, Any], field: str, **request: Any) -> int:
    answer = aws_client('dynamodb').update_item(
        TableName=table,
        Key=key,
        ExpressionAttributeNames={'#next': field},
        ExpressionAttributeValues={':one': {'N': '1'}},
        ReturnValues='UPDATED_NEW',
        **request,
    )
    return int(answer['Attributes'][field]['N']) - 1


def next_id(table: str, collection: str) -> int:
    return advance(
        table, {'PK': {'S': collection}, 'SK': {'S': COUNTER}}, 'next',
        UpdateExpression='SET #next = if_not_exists(#next, :one) + :one',
    )


def put(
    table: str, partition_key: str, sort_key: str, attributes: Dict[str, Any], **request: Any
) -> Dict[str, Any]:
    item = {'PK': {'S': partition_key}, 'SK': {'S': sort_key}, **attributes}
    aws_client('dynamodb').put_item(TableName=table, Item=item, **request)
    return item
