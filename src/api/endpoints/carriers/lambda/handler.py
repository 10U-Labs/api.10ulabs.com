import logging
import os
from functools import partial
from typing import Any, Callable, Dict, NamedTuple, Optional

from botocore.exceptions import ClientError

from lambda_http import (
    created, dispatch, error_response, has_numbers, has_strings, json_response, no_content,
    parse_fields, parse_valid, path_id,
)
from store import (
    advance, conditional, conditioned, delete, member, members, next_id, partition, put, remove,
    sort_id,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COLLECTION = 'carriers'
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


def _carrier(item: Dict[str, Any]) -> Dict[str, Any]:
    return {'id': sort_id(item), 'name': item['name']['S']}


def _list(_event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        carriers = members(os.environ['STORE_TABLE'], COLLECTION)
    except ClientError as error:
        logger.error('Error reading the carriers: %s', error)
        return error_response(500, 'Failed to read the carriers')
    return json_response(200, sorted(map(_carrier, carriers), key=lambda carrier: carrier['id']))


def _member(collection: str, member_id: str) -> Optional[Dict[str, Any]]:
    return member(os.environ['STORE_TABLE'], collection, member_id)


def _name(event: Dict[str, Any]) -> Optional[str]:
    body = parse_fields(event, ('name',))
    if body is None:
        return None
    name = body['name']
    return name if isinstance(name, str) and name else None


def _rename(collection: str, member_id: str, name: str) -> Optional[Dict[str, Any]]:
    return conditioned(
        'update_item', os.environ['STORE_TABLE'], {'PK': {'S': collection}, 'SK': {'S': member_id}},
        UpdateExpression='SET #name = :name',
        ExpressionAttributeNames={'#name': 'name'},
        ExpressionAttributeValues={':name': {'S': name}},
        ReturnValues='ALL_NEW',
    )


def _carrier_id(event: Dict[str, Any]) -> Optional[str]:
    return path_id(event, 'carrier_id')


def _read(event: Dict[str, Any]) -> Dict[str, Any]:
    carrier_id = path_id(event, 'id')
    if carrier_id is None:
        return error_response(404, MISSING)
    try:
        item = _member(COLLECTION, carrier_id)
    except ClientError as error:
        logger.error('Error reading carrier %s: %s', carrier_id, error)
        return error_response(500, 'Failed to read the carrier')
    if item is None:
        return error_response(404, MISSING)
    return json_response(200, _carrier(item))


def _update(event: Dict[str, Any]) -> Dict[str, Any]:
    name = _name(event)
    if name is None:
        return error_response(400, BODY)
    carrier_id = path_id(event, 'id')
    if carrier_id is None:
        return error_response(404, MISSING)
    try:
        item = _rename(COLLECTION, carrier_id, name)
    except ClientError as error:
        logger.error('Error renaming carrier %s: %s', carrier_id, error)
        return error_response(500, 'Failed to update the carrier')
    if item is None:
        return error_response(404, MISSING)
    return json_response(200, _carrier(item))


def _pop(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': sort_id(item),
        'municipality': item['municipality']['S'],
        'state': item['state']['S'],
        'country': item['country']['S'],
        'latitude': float(item['latitude']['N']),
        'longitude': float(item['longitude']['N']),
    }


def _fiber_segment(item: Dict[str, Any]) -> Dict[str, Any]:
    ends = {field: item[field]['S'] for field in ENDS}
    return {'id': sort_id(item), **ends, SUBMARINE: item[SUBMARINE]['BOOL']}


Row = Callable[[Dict[str, Any]], Dict[str, Any]]


def _list_under(event: Dict[str, Any], prefix: str, row: Row, failure: str) -> Dict[str, Any]:
    carrier_id = _carrier_id(event)
    if carrier_id is None:
        return error_response(404, MISSING)
    try:
        carrier = _member(COLLECTION, carrier_id)
        under = f'{COLLECTION}/{carrier_id}'
        items = partition(os.environ['STORE_TABLE'], under, f'{prefix}/') if carrier else []
    except ClientError as error:
        logger.error('Error reading the %s of carrier %s: %s', prefix, carrier_id, error)
        return error_response(500, failure)
    if carrier is None:
        return error_response(404, MISSING)
    return json_response(200, sorted(map(row, items), key=lambda one: one['id']))


def _list_pops(event: Dict[str, Any]) -> Dict[str, Any]:
    return _list_under(event, POPS, _pop, 'Failed to read the pops')


def _list_fiber_segments(event: Dict[str, Any]) -> Dict[str, Any]:
    return _list_under(event, FIBER_SEGMENTS, _fiber_segment, 'Failed to read the fiber segments')


def _delete(event: Dict[str, Any]) -> Dict[str, Any]:
    carrier_id = path_id(event, 'id')
    if carrier_id is None:
        return error_response(404, MISSING)
    try:
        removed = remove(os.environ['STORE_TABLE'], COLLECTION, carrier_id)
    except ClientError as error:
        logger.error('Error deleting carrier %s: %s', carrier_id, error)
        return error_response(500, 'Failed to delete the carrier')
    if not removed:
        return error_response(404, MISSING)
    return no_content()


def _create(event: Dict[str, Any]) -> Dict[str, Any]:
    name = _name(event)
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
    return created(f'/{COLLECTION}/{carrier_id}', {'id': carrier_id, 'name': name})


def _next_under(carrier_id: str, counter: str) -> Optional[int]:
    try:
        return advance(
            os.environ['STORE_TABLE'], {'PK': {'S': COLLECTION}, 'SK': {'S': carrier_id}}, counter,
            ConditionExpression='attribute_exists(PK)',
            UpdateExpression='SET #next = #next + :one',
        )
    except ClientError as error:
        if conditional(error):
            return None
        raise


def _pop_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return parse_valid(
        event, PLACE + COORDINATES,
        lambda body: has_strings(body, PLACE, NAMED) and has_numbers(body, COORDINATES),
    )


def _fiber_segment_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return parse_valid(
        event, ENDS + (SUBMARINE,),
        lambda body: has_strings(body, ENDS, SPANNED) and isinstance(body[SUBMARINE], bool),
    )


def _put_under(
    carrier_id: str, prefix: str, member_id: str, attributes: Dict[str, Any], **request: Any
) -> Dict[str, Any]:
    table = os.environ['STORE_TABLE']
    return put(table, f'{COLLECTION}/{carrier_id}', f'{prefix}/{member_id}', attributes, **request)


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
    missing: str
    counter: str
    body: Body
    refusal: str
    put: Put
    row: Row
    failure: str


POP_KIND = Kind(
    POPS, MISSING_POP, 'next_pop', _pop_body, POP_BODY, _put_pop, _pop,
    'Failed to add the pop',
)
FIBER_SEGMENT_KIND = Kind(
    FIBER_SEGMENTS, MISSING_FIBER_SEGMENT, 'next_fiber_segment',
    _fiber_segment_body, FIBER_SEGMENT_BODY, _put_fiber_segment, _fiber_segment,
    'Failed to add the fiber segment',
)


def _add_under(event: Dict[str, Any], kind: Kind) -> Dict[str, Any]:
    body = kind.body(event)
    if body is None:
        return error_response(400, kind.refusal)
    carrier_id = _carrier_id(event)
    if carrier_id is None:
        return error_response(404, MISSING)
    try:
        member_id = _next_under(carrier_id, kind.counter)
        item = kind.put(carrier_id, str(member_id), body) if member_id is not None else None
    except ClientError as error:
        logger.error('Error adding to the %s of carrier %s: %s', kind.prefix, carrier_id, error)
        return error_response(500, kind.failure)
    if item is None:
        return error_response(404, MISSING)
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
        return error_response(404, MISSING)
    member_id = path_id(event, 'id')
    if member_id is None:
        return error_response(404, kind.missing)
    try:
        carrier = _member(COLLECTION, carrier_id)
        item = act(carrier_id, member_id) if carrier else None
    except ClientError as error:
        logger.error(
            'Error with %s/%s of carrier %s: %s', kind.prefix, member_id, carrier_id, error
        )
        return error_response(500, failure)
    if carrier is None:
        return error_response(404, MISSING)
    if item is None:
        return error_response(404, kind.missing)
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
        if conditional(error):
            return None
        raise


def _update_under(event: Dict[str, Any], kind: Kind, failure: str) -> Dict[str, Any]:
    body = kind.body(event)
    if body is None:
        return error_response(400, kind.refusal)
    return _on_member(event, kind, partial(_replace_under, kind=kind, body=body), failure)


def _update_pop(event: Dict[str, Any]) -> Dict[str, Any]:
    return _update_under(event, POP_KIND, 'Failed to update the pop')


def _update_fiber_segment(event: Dict[str, Any]) -> Dict[str, Any]:
    return _update_under(event, FIBER_SEGMENT_KIND, 'Failed to update the fiber segment')


def _remove_under(carrier_id: str, member_id: str, prefix: str) -> Optional[Dict[str, Any]]:
    table = os.environ['STORE_TABLE']
    return delete(table, f'{COLLECTION}/{carrier_id}', f'{prefix}/{member_id}')


def _delete_under(event: Dict[str, Any], kind: Kind, failure: str) -> Dict[str, Any]:
    removed = partial(_remove_under, prefix=kind.prefix)
    return _on_member(event, kind, removed, failure, lambda _gone: no_content())


def _delete_pop(event: Dict[str, Any]) -> Dict[str, Any]:
    return _delete_under(event, POP_KIND, 'Failed to delete the pop')


def _delete_fiber_segment(event: Dict[str, Any]) -> Dict[str, Any]:
    return _delete_under(event, FIBER_SEGMENT_KIND, 'Failed to delete the fiber segment')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {
        ('/carriers', 'GET'): _list,
        ('/carriers', 'POST'): _create,
        ('/carriers/{id}', 'GET'): _read,
        ('/carriers/{id}', 'PUT'): _update,
        ('/carriers/{id}', 'DELETE'): _delete,
        ('/carriers/{carrier_id}/pops', 'GET'): _list_pops,
        ('/carriers/{carrier_id}/pops', 'POST'): _add_pop,
        ('/carriers/{carrier_id}/pops/{id}', 'GET'): _read_pop,
        ('/carriers/{carrier_id}/pops/{id}', 'PUT'): _update_pop,
        ('/carriers/{carrier_id}/pops/{id}', 'DELETE'): _delete_pop,
        ('/carriers/{carrier_id}/fiber-segments', 'GET'): _list_fiber_segments,
        ('/carriers/{carrier_id}/fiber-segments', 'POST'): _add_fiber_segment,
        ('/carriers/{carrier_id}/fiber-segments/{id}', 'GET'): _read_fiber_segment,
        ('/carriers/{carrier_id}/fiber-segments/{id}', 'PUT'): _update_fiber_segment,
        ('/carriers/{carrier_id}/fiber-segments/{id}', 'DELETE'): _delete_fiber_segment,
    })
