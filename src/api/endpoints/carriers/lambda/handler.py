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
MISSING = 'No such carrier'
MISSING_POP = 'No such pop'
POPS = 'pops'
PLACE = ('municipality', 'state', 'country')
NAMED = ('municipality', 'country')
COORDINATES = ('latitude', 'longitude')
POP_BODY = 'The body must be exactly {"municipality", "state", "country", "latitude", "longitude"}'


def _partition(partition: str, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
    condition = 'PK = :pk'
    values = {':pk': {'S': partition}}
    if prefix is not None:
        condition += ' AND begins_with(SK, :prefix)'
        values[':prefix'] = {'S': prefix}
    answer = aws_client('dynamodb').query(
        TableName=os.environ['STORE_TABLE'],
        KeyConditionExpression=condition,
        ExpressionAttributeValues=values,
    )
    items: List[Dict[str, Any]] = answer['Items']
    return items


def _members(collection: str) -> List[Dict[str, Any]]:
    return [item for item in _partition(collection) if item['SK']['S'] != COUNTER]


def _carrier(item: Dict[str, Any]) -> Dict[str, Any]:
    return {'id': int(item['SK']['S']), 'name': item['name']['S']}


def _list(_event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        members = _members(COLLECTION)
    except ClientError as error:
        logger.error('Error reading the carriers: %s', error)
        return json_response(500, {'error': 'Failed to read the carriers'})
    return json_response(200, sorted(map(_carrier, members), key=lambda carrier: carrier['id']))


def _member(collection: str, member_id: str) -> Optional[Dict[str, Any]]:
    answer = aws_client('dynamodb').get_item(
        TableName=os.environ['STORE_TABLE'],
        Key={'PK': {'S': collection}, 'SK': {'S': member_id}},
    )
    item: Optional[Dict[str, Any]] = answer.get('Item')
    return item


def _name(event: Dict[str, Any]) -> Optional[str]:
    body = parse_object(event)
    if body is None or set(body) != {'name'}:
        return None
    name = body['name']
    return name if isinstance(name, str) and name else None


def _conditional(error: ClientError) -> bool:
    code: str = error.response['Error']['Code']
    return code == 'ConditionalCheckFailedException'


def _rename(collection: str, member_id: str, name: str) -> Optional[Dict[str, Any]]:
    try:
        answer = aws_client('dynamodb').update_item(
            TableName=os.environ['STORE_TABLE'],
            Key={'PK': {'S': collection}, 'SK': {'S': member_id}},
            ConditionExpression='attribute_exists(PK)',
            UpdateExpression='SET #name = :name',
            ExpressionAttributeNames={'#name': 'name'},
            ExpressionAttributeValues={':name': {'S': name}},
            ReturnValues='ALL_NEW',
        )
    except ClientError as error:
        if _conditional(error):
            return None
        raise
    item: Dict[str, Any] = answer['Attributes']
    return item


def _path_id(event: Dict[str, Any], name: str) -> Optional[str]:
    member_id = str((event.get('pathParameters') or {}).get(name) or '')
    return member_id if member_id.isdigit() else None


def _carrier_id(event: Dict[str, Any]) -> Optional[str]:
    return _path_id(event, 'carrier')


def _read(event: Dict[str, Any]) -> Dict[str, Any]:
    carrier_id = _carrier_id(event)
    if carrier_id is None:
        return json_response(404, {'error': MISSING})
    try:
        item = _member(COLLECTION, carrier_id)
    except ClientError as error:
        logger.error('Error reading carrier %s: %s', carrier_id, error)
        return json_response(500, {'error': 'Failed to read the carrier'})
    if item is None:
        return json_response(404, {'error': MISSING})
    return json_response(200, _carrier(item))


def _update(event: Dict[str, Any]) -> Dict[str, Any]:
    name = _name(event)
    if name is None:
        return json_response(400, {'error': BODY})
    carrier_id = _carrier_id(event)
    if carrier_id is None:
        return json_response(404, {'error': MISSING})
    try:
        item = _rename(COLLECTION, carrier_id, name)
    except ClientError as error:
        logger.error('Error renaming carrier %s: %s', carrier_id, error)
        return json_response(500, {'error': 'Failed to update the carrier'})
    if item is None:
        return json_response(404, {'error': MISSING})
    return json_response(200, _carrier(item))


def _remove(collection: str, member_id: str) -> bool:
    table = os.environ['STORE_TABLE']
    store = aws_client('dynamodb')
    for item in _partition(f'{collection}/{member_id}'):
        store.delete_item(TableName=table, Key={'PK': item['PK'], 'SK': item['SK']})
    try:
        store.delete_item(
            TableName=table,
            Key={'PK': {'S': collection}, 'SK': {'S': member_id}},
            ConditionExpression='attribute_exists(PK)',
        )
    except ClientError as error:
        if _conditional(error):
            return False
        raise
    return True


def _pop(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': int(item['SK']['S'].partition('/')[2]),
        'municipality': item['municipality']['S'],
        'state': item['state']['S'],
        'country': item['country']['S'],
        'latitude': float(item['latitude']['N']),
        'longitude': float(item['longitude']['N']),
    }


def _list_pops(event: Dict[str, Any]) -> Dict[str, Any]:
    carrier_id = _carrier_id(event)
    if carrier_id is None:
        return json_response(404, {'error': MISSING})
    try:
        carrier = _member(COLLECTION, carrier_id)
        pops = _partition(f'{COLLECTION}/{carrier_id}', f'{POPS}/') if carrier else []
    except ClientError as error:
        logger.error('Error reading the pops of carrier %s: %s', carrier_id, error)
        return json_response(500, {'error': 'Failed to read the pops'})
    if carrier is None:
        return json_response(404, {'error': MISSING})
    return json_response(200, sorted(map(_pop, pops), key=lambda pop: pop['id']))


def _read_pop(event: Dict[str, Any]) -> Dict[str, Any]:
    carrier_id = _carrier_id(event)
    if carrier_id is None:
        return json_response(404, {'error': MISSING})
    pop_id = _path_id(event, 'pop')
    if pop_id is None:
        return json_response(404, {'error': MISSING_POP})
    try:
        carrier = _member(COLLECTION, carrier_id)
        pop = _member(f'{COLLECTION}/{carrier_id}', f'{POPS}/{pop_id}') if carrier else None
    except ClientError as error:
        logger.error('Error reading pop %s of carrier %s: %s', pop_id, carrier_id, error)
        return json_response(500, {'error': 'Failed to read the pop'})
    if carrier is None:
        return json_response(404, {'error': MISSING})
    if pop is None:
        return json_response(404, {'error': MISSING_POP})
    return json_response(200, _pop(pop))


def _delete(event: Dict[str, Any]) -> Dict[str, Any]:
    carrier_id = _carrier_id(event)
    if carrier_id is None:
        return json_response(404, {'error': MISSING})
    try:
        removed = _remove(COLLECTION, carrier_id)
    except ClientError as error:
        logger.error('Error deleting carrier %s: %s', carrier_id, error)
        return json_response(500, {'error': 'Failed to delete the carrier'})
    if not removed:
        return json_response(404, {'error': MISSING})
    return {'statusCode': 204, 'headers': {}, 'body': ''}


def _advance(key: Dict[str, Any], field: str, **request: Any) -> int:
    answer = aws_client('dynamodb').update_item(
        TableName=os.environ['STORE_TABLE'],
        Key=key,
        ExpressionAttributeNames={'#next': field},
        ExpressionAttributeValues={':one': {'N': '1'}},
        ReturnValues='UPDATED_NEW',
        **request,
    )
    return int(answer['Attributes'][field]['N']) - 1


def _next_id(collection: str) -> int:
    return _advance(
        {'PK': {'S': collection}, 'SK': {'S': COUNTER}}, 'next',
        UpdateExpression='SET #next = if_not_exists(#next, :one) + :one',
    )


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


def _next_pop_id(carrier_id: str) -> Optional[int]:
    try:
        return _advance(
            {'PK': {'S': COLLECTION}, 'SK': {'S': carrier_id}}, 'next_pop',
            ConditionExpression='attribute_exists(PK)',
            UpdateExpression='SET #next = #next + :one',
        )
    except ClientError as error:
        if _conditional(error):
            return None
        raise


def _placed(body: Dict[str, Any]) -> bool:
    worded = all(isinstance(body[field], str) for field in PLACE)
    return worded and all(body[field] for field in NAMED)


def _located(body: Dict[str, Any]) -> bool:
    return all(
        isinstance(body[field], (int, float)) and not isinstance(body[field], bool)
        for field in COORDINATES
    )


def _pop_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    body = parse_object(event)
    if body is None or set(body) != set(PLACE + COORDINATES):
        return None
    return body if _placed(body) and _located(body) else None


def _put_pop(carrier_id: str, pop_id: int, body: Dict[str, Any]) -> Dict[str, Any]:
    item = {
        'PK': {'S': f'{COLLECTION}/{carrier_id}'},
        'SK': {'S': f'{POPS}/{pop_id}'},
        **{field: {'S': body[field]} for field in PLACE},
        **{field: {'N': str(body[field])} for field in COORDINATES},
    }
    aws_client('dynamodb').put_item(TableName=os.environ['STORE_TABLE'], Item=item)
    return item


def _add_pop(event: Dict[str, Any]) -> Dict[str, Any]:
    body = _pop_body(event)
    if body is None:
        return json_response(400, {'error': POP_BODY})
    carrier_id = _carrier_id(event)
    if carrier_id is None:
        return json_response(404, {'error': MISSING})
    try:
        pop_id = _next_pop_id(carrier_id)
        item = _put_pop(carrier_id, pop_id, body) if pop_id is not None else None
    except ClientError as error:
        logger.error('Error adding a pop to carrier %s: %s', carrier_id, error)
        return json_response(500, {'error': 'Failed to add the pop'})
    if item is None:
        return json_response(404, {'error': MISSING})
    response = json_response(201, _pop(item))
    response['headers']['Location'] = f'/{COLLECTION}/{carrier_id}/{POPS}/{pop_id}'
    return response


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {
        ('/carriers', 'GET'): _list,
        ('/carriers', 'POST'): _create,
        ('/carriers/{carrier}', 'GET'): _read,
        ('/carriers/{carrier}', 'PUT'): _update,
        ('/carriers/{carrier}', 'DELETE'): _delete,
        ('/carriers/{carrier}/pops', 'GET'): _list_pops,
        ('/carriers/{carrier}/pops', 'POST'): _add_pop,
        ('/carriers/{carrier}/pops/{pop}', 'GET'): _read_pop,
    })
