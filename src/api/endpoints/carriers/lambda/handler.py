import logging
import os
from functools import partial
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple

from botocore.exceptions import ClientError

from lambda_http import aws_client, created, dispatch, json_response, parse_fields

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COLLECTION = 'carriers'
COUNTER = '#'
BODY = 'The body must be exactly {"name"}'
MISSING = 'No such carrier'
MISSING_POP = 'No such pop'
MISSING_FIBER_SEGMENT = 'No such fiber segment'
POPS = 'pops'
FIBER_SEGMENTS = 'fiber-segments'
ENDS = ('a_municipality', 'a_state', 'z_municipality', 'z_state')
SPANNED = ('a_municipality', 'z_municipality')
SUBMARINE = 'submarine'
PLACE = ('municipality', 'state', 'country')
NAMED = ('municipality', 'country')
COORDINATES = ('latitude', 'longitude')
POP_BODY = 'The body must be exactly {"municipality", "state", "country", "latitude", "longitude"}'
FIBER_SEGMENT_BODY = (
    'The body must be exactly '
    '{"a_municipality", "a_state", "z_municipality", "z_state", "submarine"}'
)


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
    body = parse_fields(event, ('name',))
    if body is None:
        return None
    name = body['name']
    return name if isinstance(name, str) and name else None


def _conditional(error: ClientError) -> bool:
    code: str = error.response['Error']['Code']
    return code == 'ConditionalCheckFailedException'


def _attributes(write: str, key: Dict[str, Any], **request: Any) -> Optional[Dict[str, Any]]:
    try:
        answer = getattr(aws_client('dynamodb'), write)(
            TableName=os.environ['STORE_TABLE'],
            Key=key,
            ConditionExpression='attribute_exists(PK)',
            **request,
        )
    except ClientError as error:
        if _conditional(error):
            return None
        raise
    item: Dict[str, Any] = answer['Attributes']
    return item


def _rename(collection: str, member_id: str, name: str) -> Optional[Dict[str, Any]]:
    return _attributes(
        'update_item', {'PK': {'S': collection}, 'SK': {'S': member_id}},
        UpdateExpression='SET #name = :name',
        ExpressionAttributeNames={'#name': 'name'},
        ExpressionAttributeValues={':name': {'S': name}},
        ReturnValues='ALL_NEW',
    )


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


def _id_under(item: Dict[str, Any]) -> int:
    return int(item['SK']['S'].partition('/')[2])


def _pop(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': _id_under(item),
        'municipality': item['municipality']['S'],
        'state': item['state']['S'],
        'country': item['country']['S'],
        'latitude': float(item['latitude']['N']),
        'longitude': float(item['longitude']['N']),
    }


def _fiber_segment(item: Dict[str, Any]) -> Dict[str, Any]:
    ends = {field: item[field]['S'] for field in ENDS}
    return {'id': _id_under(item), **ends, SUBMARINE: item[SUBMARINE]['BOOL']}


Row = Callable[[Dict[str, Any]], Dict[str, Any]]


def _list_under(event: Dict[str, Any], prefix: str, row: Row, failure: str) -> Dict[str, Any]:
    carrier_id = _carrier_id(event)
    if carrier_id is None:
        return json_response(404, {'error': MISSING})
    try:
        carrier = _member(COLLECTION, carrier_id)
        items = _partition(f'{COLLECTION}/{carrier_id}', f'{prefix}/') if carrier else []
    except ClientError as error:
        logger.error('Error reading the %s of carrier %s: %s', prefix, carrier_id, error)
        return json_response(500, {'error': failure})
    if carrier is None:
        return json_response(404, {'error': MISSING})
    return json_response(200, sorted(map(row, items), key=lambda one: one['id']))


def _list_pops(event: Dict[str, Any]) -> Dict[str, Any]:
    return _list_under(event, POPS, _pop, 'Failed to read the pops')


def _list_fiber_segments(event: Dict[str, Any]) -> Dict[str, Any]:
    return _list_under(event, FIBER_SEGMENTS, _fiber_segment, 'Failed to read the fiber segments')


def _no_content() -> Dict[str, Any]:
    return {'statusCode': 204, 'headers': {}, 'body': ''}


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
    return _no_content()


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
    return created(f'/{COLLECTION}/{carrier_id}', {'id': carrier_id, 'name': name})


def _next_under(carrier_id: str, counter: str) -> Optional[int]:
    try:
        return _advance(
            {'PK': {'S': COLLECTION}, 'SK': {'S': carrier_id}}, counter,
            ConditionExpression='attribute_exists(PK)',
            UpdateExpression='SET #next = #next + :one',
        )
    except ClientError as error:
        if _conditional(error):
            return None
        raise


def _worded(body: Dict[str, Any], fields: Tuple[str, ...], named: Tuple[str, ...]) -> bool:
    worded = all(isinstance(body[field], str) for field in fields)
    return worded and all(body[field] for field in named)


def _located(body: Dict[str, Any]) -> bool:
    return all(
        isinstance(body[field], (int, float)) and not isinstance(body[field], bool)
        for field in COORDINATES
    )


Valid = Callable[[Dict[str, Any]], bool]


def _body(event: Dict[str, Any], fields: Tuple[str, ...], valid: Valid) -> Optional[Dict[str, Any]]:
    body = parse_fields(event, fields)
    return body if body is not None and valid(body) else None


def _pop_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return _body(
        event, PLACE + COORDINATES, lambda body: _worded(body, PLACE, NAMED) and _located(body)
    )


def _fiber_segment_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return _body(
        event, ENDS + (SUBMARINE,),
        lambda body: _worded(body, ENDS, SPANNED) and isinstance(body[SUBMARINE], bool),
    )


def _put_under(
    carrier_id: str, prefix: str, member_id: str, attributes: Dict[str, Any], **request: Any
) -> Dict[str, Any]:
    item = {
        'PK': {'S': f'{COLLECTION}/{carrier_id}'},
        'SK': {'S': f'{prefix}/{member_id}'},
        **attributes,
    }
    aws_client('dynamodb').put_item(TableName=os.environ['STORE_TABLE'], Item=item, **request)
    return item


def _put_pop(
    carrier_id: str, pop_id: str, body: Dict[str, Any], **request: Any
) -> Dict[str, Any]:
    return _put_under(carrier_id, POPS, pop_id, {
        **{field: {'S': body[field]} for field in PLACE},
        **{field: {'N': str(body[field])} for field in COORDINATES},
    }, **request)


def _put_fiber_segment(
    carrier_id: str, segment_id: str, body: Dict[str, Any], **request: Any
) -> Dict[str, Any]:
    return _put_under(carrier_id, FIBER_SEGMENTS, segment_id, {
        **{field: {'S': body[field]} for field in ENDS},
        SUBMARINE: {'BOOL': body[SUBMARINE]},
    }, **request)


Body = Callable[[Dict[str, Any]], Optional[Dict[str, Any]]]
Put = Callable[..., Dict[str, Any]]


class Kind(NamedTuple):
    prefix: str
    parameter: str
    missing: str
    counter: str
    body: Body
    refusal: str
    put: Put
    row: Row
    failure: str


POP_KIND = Kind(
    POPS, 'pop', MISSING_POP, 'next_pop', _pop_body, POP_BODY, _put_pop, _pop,
    'Failed to add the pop',
)
FIBER_SEGMENT_KIND = Kind(
    FIBER_SEGMENTS, 'fiber-segment', MISSING_FIBER_SEGMENT, 'next_fiber_segment',
    _fiber_segment_body, FIBER_SEGMENT_BODY, _put_fiber_segment, _fiber_segment,
    'Failed to add the fiber segment',
)


def _add_under(event: Dict[str, Any], kind: Kind) -> Dict[str, Any]:
    body = kind.body(event)
    if body is None:
        return json_response(400, {'error': kind.refusal})
    carrier_id = _carrier_id(event)
    if carrier_id is None:
        return json_response(404, {'error': MISSING})
    try:
        member_id = _next_under(carrier_id, kind.counter)
        item = kind.put(carrier_id, str(member_id), body) if member_id is not None else None
    except ClientError as error:
        logger.error('Error adding to the %s of carrier %s: %s', kind.prefix, carrier_id, error)
        return json_response(500, {'error': kind.failure})
    if item is None:
        return json_response(404, {'error': MISSING})
    return created(f'/{COLLECTION}/{carrier_id}/{kind.prefix}/{member_id}', kind.row(item))


def _add_pop(event: Dict[str, Any]) -> Dict[str, Any]:
    return _add_under(event, POP_KIND)


def _add_fiber_segment(event: Dict[str, Any]) -> Dict[str, Any]:
    return _add_under(event, FIBER_SEGMENT_KIND)


Act = Callable[[str, str], Optional[Dict[str, Any]]]
Answer = Callable[[Dict[str, Any]], Dict[str, Any]]


def _on_member(
    event: Dict[str, Any], kind: Kind, act: Act, failure: str, answer: Optional[Answer] = None
) -> Dict[str, Any]:
    carrier_id = _carrier_id(event)
    if carrier_id is None:
        return json_response(404, {'error': MISSING})
    member_id = _path_id(event, kind.parameter)
    if member_id is None:
        return json_response(404, {'error': kind.missing})
    try:
        carrier = _member(COLLECTION, carrier_id)
        item = act(carrier_id, member_id) if carrier else None
    except ClientError as error:
        logger.error(
            'Error with %s %s of carrier %s: %s', kind.parameter, member_id, carrier_id, error
        )
        return json_response(500, {'error': failure})
    if carrier is None:
        return json_response(404, {'error': MISSING})
    if item is None:
        return json_response(404, {'error': kind.missing})
    return answer(item) if answer else json_response(200, kind.row(item))


def _stored_under(carrier_id: str, member_id: str, prefix: str) -> Optional[Dict[str, Any]]:
    return _member(f'{COLLECTION}/{carrier_id}', f'{prefix}/{member_id}')


def _read_pop(event: Dict[str, Any]) -> Dict[str, Any]:
    stored = partial(_stored_under, prefix=POPS)
    return _on_member(event, POP_KIND, stored, 'Failed to read the pop')


def _read_fiber_segment(event: Dict[str, Any]) -> Dict[str, Any]:
    stored = partial(_stored_under, prefix=FIBER_SEGMENTS)
    return _on_member(event, FIBER_SEGMENT_KIND, stored, 'Failed to read the fiber segment')


def _replace_under(
    carrier_id: str, member_id: str, kind: Kind, body: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    try:
        return kind.put(carrier_id, member_id, body, ConditionExpression='attribute_exists(PK)')
    except ClientError as error:
        if _conditional(error):
            return None
        raise


def _update_under(event: Dict[str, Any], kind: Kind, failure: str) -> Dict[str, Any]:
    body = kind.body(event)
    if body is None:
        return json_response(400, {'error': kind.refusal})
    return _on_member(event, kind, partial(_replace_under, kind=kind, body=body), failure)


def _update_pop(event: Dict[str, Any]) -> Dict[str, Any]:
    return _update_under(event, POP_KIND, 'Failed to update the pop')


def _update_fiber_segment(event: Dict[str, Any]) -> Dict[str, Any]:
    return _update_under(event, FIBER_SEGMENT_KIND, 'Failed to update the fiber segment')


def _remove_pop(carrier_id: str, pop_id: str) -> Optional[Dict[str, Any]]:
    key = {'PK': {'S': f'{COLLECTION}/{carrier_id}'}, 'SK': {'S': f'{POPS}/{pop_id}'}}
    return _attributes('delete_item', key, ReturnValues='ALL_OLD')


def _delete_pop(event: Dict[str, Any]) -> Dict[str, Any]:
    return _on_member(
        event, POP_KIND, _remove_pop, 'Failed to delete the pop', lambda _gone: _no_content()
    )


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
        ('/carriers/{carrier}/pops/{pop}', 'PUT'): _update_pop,
        ('/carriers/{carrier}/pops/{pop}', 'DELETE'): _delete_pop,
        ('/carriers/{carrier}/fiber-segments', 'GET'): _list_fiber_segments,
        ('/carriers/{carrier}/fiber-segments', 'POST'): _add_fiber_segment,
        ('/carriers/{carrier}/fiber-segments/{fiber-segment}', 'GET'): _read_fiber_segment,
        ('/carriers/{carrier}/fiber-segments/{fiber-segment}', 'PUT'): _update_fiber_segment,
    })
