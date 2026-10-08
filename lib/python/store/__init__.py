from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError

from lambda_http import aws_client

COUNTER = '#'
BATCH = 25


def partition(table: str, key: str, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
    condition = 'PK = :pk'
    values = {':pk': {'S': key}}
    if prefix is not None:
        condition += ' AND begins_with(SK, :prefix)'
        values[':prefix'] = {'S': prefix}
    store = aws_client('dynamodb')
    request: Dict[str, Any] = {
        'TableName': table,
        'KeyConditionExpression': condition,
        'ExpressionAttributeValues': values,
    }
    pages = [store.query(**request)]
    while 'LastEvaluatedKey' in pages[-1]:
        pages.append(store.query(**request, ExclusiveStartKey=pages[-1]['LastEvaluatedKey']))
    return [item for page in pages for item in page['Items']]


def members(table: str, collection: str) -> List[Dict[str, Any]]:
    return [item for item in partition(table, collection) if item['SK']['S'] != COUNTER]


def member(table: str, collection: str, member_id: str) -> Optional[Dict[str, Any]]:
    answer = aws_client('dynamodb').get_item(
        TableName=table,
        Key={'PK': {'S': collection}, 'SK': {'S': member_id}},
    )
    item: Optional[Dict[str, Any]] = answer.get('Item')
    return item


def _moved(table: str, key: Dict[str, Any], field: str, count: int, **request: Any) -> int:
    answer = aws_client('dynamodb').update_item(
        TableName=table,
        Key=key,
        ExpressionAttributeNames={'#next': field},
        ReturnValues='UPDATED_NEW',
        **request,
    )
    return int(answer['Attributes'][field]['N']) - count


def advance(table: str, key: Dict[str, Any], field: str, **request: Any) -> int:
    return _moved(table, key, field, 1, ExpressionAttributeValues={':one': {'N': '1'}}, **request)


def reserve(table: str, key: Dict[str, Any], field: str, count: int, **request: Any) -> int:
    return _moved(
        table, key, field, count,
        UpdateExpression='SET #next = if_not_exists(#next, :one) + :count',
        ExpressionAttributeValues={':one': {'N': '1'}, ':count': {'N': str(count)}},
        **request,
    )


def next_id(table: str, collection: str) -> int:
    return reserve(table, {'PK': {'S': collection}, 'SK': {'S': COUNTER}}, 'next', 1)


def put(
    table: str, partition_key: str, sort_key: str, attributes: Dict[str, Any], **request: Any
) -> Dict[str, Any]:
    item = {'PK': {'S': partition_key}, 'SK': {'S': sort_key}, **attributes}
    aws_client('dynamodb').put_item(TableName=table, Item=item, **request)
    return item


def conditional(error: ClientError) -> bool:
    code: str = error.response['Error']['Code']
    return code == 'ConditionalCheckFailedException'


def conditioned(
    write: str, table: str, key: Dict[str, Any], **request: Any
) -> Optional[Dict[str, Any]]:
    try:
        answer = getattr(aws_client('dynamodb'), write)(
            TableName=table,
            Key=key,
            ConditionExpression='attribute_exists(PK)',
            **request,
        )
    except ClientError as error:
        if conditional(error):
            return None
        raise
    item: Dict[str, Any] = answer['Attributes']
    return item


def typed(value: Any) -> Dict[str, Any]:
    if isinstance(value, bool):
        return {'BOOL': value}
    if isinstance(value, (int, float)):
        return {'N': str(value)}
    if isinstance(value, dict):
        return {'M': {field: typed(inner) for field, inner in value.items()}}
    if isinstance(value, list):
        return {'L': [typed(inner) for inner in value]}
    return {'NULL': True} if value is None else {'S': str(value)}


def assign(
    table: str, partition_key: str, sort_key: str, attributes: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    placed = list(enumerate(attributes.items()))
    return conditioned(
        'update_item', table, {'PK': {'S': partition_key}, 'SK': {'S': sort_key}},
        UpdateExpression='SET ' + ', '.join(f'#{index} = :{index}' for index, _ in placed),
        ExpressionAttributeNames={f'#{index}': field for index, (field, _) in placed},
        ExpressionAttributeValues={f':{index}': typed(value) for index, (_, value) in placed},
        ReturnValues='ALL_NEW',
    )


def delete(table: str, partition_key: str, sort_key: str) -> Optional[Dict[str, Any]]:
    key = {'PK': {'S': partition_key}, 'SK': {'S': sort_key}}
    return conditioned('delete_item', table, key, ReturnValues='ALL_OLD')


def batch_write(table: str, requests: List[Dict[str, Any]]) -> None:
    store = aws_client('dynamodb')
    for start in range(0, len(requests), BATCH):
        pending = requests[start:start + BATCH]
        while pending:
            answer = store.batch_write_item(RequestItems={table: pending})
            pending = answer.get('UnprocessedItems', {}).get(table, [])


def remove(table: str, collection: str, member_id: str) -> bool:
    store = aws_client('dynamodb')
    under = partition(table, f'{collection}/{member_id}')
    batch_write(table, [
        {'DeleteRequest': {'Key': {'PK': item['PK'], 'SK': item['SK']}}} for item in under
    ])
    try:
        store.delete_item(
            TableName=table,
            Key={'PK': {'S': collection}, 'SK': {'S': member_id}},
            ConditionExpression='attribute_exists(PK)',
        )
    except ClientError as error:
        if conditional(error):
            return False
        raise
    return True


def plain(value: Dict[str, Any]) -> Any:
    kind, held = next(iter(value.items()))
    if kind == 'N':
        return int(held) if held.lstrip('-').isdigit() else float(held)
    if kind == 'M':
        return {field: plain(inner) for field, inner in held.items()}
    if kind == 'L':
        return [plain(inner) for inner in held]
    return None if kind == 'NULL' else held


def sort_id(item: Dict[str, Any]) -> int:
    sort_key: str = item['SK']['S']
    return int(sort_key.rpartition('/')[2])
