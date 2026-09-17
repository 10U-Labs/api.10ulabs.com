import os
from functools import partial
from typing import Any, Callable, Dict, NamedTuple, Optional

from botocore.exceptions import ClientError

from carriers import COLLECTION, MISSING, held, logger, requested
from lambda_http import (
    created, dispatch, error_response, has_numbers, has_strings, json_response, no_content,
    parse_valid, path_id,
)
from store import advance, conditional, delete, partition, put, sort_id

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
    carrier_id = requested(event)
    if carrier_id is None:
        return error_response(404, MISSING)
    try:
        carrier = held(COLLECTION, carrier_id)
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
    parameter: str
    missing: str
    counter: str
    body: Body
    refusal: str
    put: Put
    row: Row
    failure: str


POP_KIND = Kind(
    POPS, 'pop_id', MISSING_POP, 'next_pop', _pop_body, POP_BODY, _put_pop, _pop,
    'Failed to add the pop',
)
FIBER_SEGMENT_KIND = Kind(
    FIBER_SEGMENTS, 'fiber_segment_id', MISSING_FIBER_SEGMENT, 'next_fiber_segment',
    _fiber_segment_body, FIBER_SEGMENT_BODY, _put_fiber_segment, _fiber_segment,
    'Failed to add the fiber segment',
)


def _add_under(event: Dict[str, Any], kind: Kind) -> Dict[str, Any]:
    body = kind.body(event)
    if body is None:
        return error_response(400, kind.refusal)
    carrier_id = requested(event)
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
    carrier_id = requested(event)
    if carrier_id is None:
        return error_response(404, MISSING)
    member_id = path_id(event, kind.parameter)
    if member_id is None:
        return error_response(404, kind.missing)
    try:
        carrier = held(COLLECTION, carrier_id)
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
    return held(f'{COLLECTION}/{carrier_id}', f'{prefix}/{member_id}')


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
        ('/carriers/{id}/pops', 'GET'): _list_pops,
        ('/carriers/{id}/pops', 'POST'): _add_pop,
        ('/carriers/{id}/pops/{pop_id}', 'GET'): _read_pop,
        ('/carriers/{id}/pops/{pop_id}', 'PUT'): _update_pop,
        ('/carriers/{id}/pops/{pop_id}', 'DELETE'): _delete_pop,
        ('/carriers/{id}/fiber-segments', 'GET'): _list_fiber_segments,
        ('/carriers/{id}/fiber-segments', 'POST'): _add_fiber_segment,
        ('/carriers/{id}/fiber-segments/{fiber_segment_id}', 'GET'): _read_fiber_segment,
        ('/carriers/{id}/fiber-segments/{fiber_segment_id}', 'PUT'): _update_fiber_segment,
        ('/carriers/{id}/fiber-segments/{fiber_segment_id}', 'DELETE'): _delete_fiber_segment,
    })
