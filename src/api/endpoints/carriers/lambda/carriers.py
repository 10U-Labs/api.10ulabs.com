import logging
import os
from functools import partial
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple

from botocore.exceptions import ClientError

from cache import invalidate
from lambda_http import (
    Valid, created, error_response, has_numbers, has_strings, json_response, no_content,
    parse_body, parse_fields, parse_valid, path_id,
)
from store import (
    batch_write, conditional, delete, member, partition, put, reserve, sort_id,
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
PLACE = ('municipality', 'state', 'country')
NAMED = ('municipality', 'country')
COORDINATES = ('latitude', 'longitude')
ENDS = ('a_municipality', 'a_state', 'z_municipality', 'z_state')
SPANNED = ('a_municipality', 'z_municipality')
SUBMARINE = 'submarine'
POP_BODY = 'The body must be exactly {"municipality", "state", "country", "latitude", "longitude"}'
FIBER_SEGMENT_BODY = (
    'The body must be exactly '
    '{"a_municipality", "a_state", "z_municipality", "z_state", "submarine"}'
)
POPS_BODY = (
    'The body must be a list of '
    '{"municipality", "state", "country", "latitude", "longitude"}'
)
FIBER_SEGMENTS_BODY = (
    'The body must be a list of '
    '{"a_municipality", "a_state", "z_municipality", "z_state", "submarine"}'
)


def carrier(item: Dict[str, Any]) -> Dict[str, Any]:
    return {'id': sort_id(item), 'name': item['name']['S']}


def requested(event: Dict[str, Any]) -> Optional[str]:
    return path_id(event, 'id')


def held(collection: str, member_id: str) -> Optional[Dict[str, Any]]:
    return member(os.environ['STORE_TABLE'], collection, member_id)


def staled(carrier_id: str, *deeper: str) -> None:
    invalidate([f'/{COLLECTION}', f'/{COLLECTION}/{carrier_id}', *deeper])


def staled_under(carrier_id: str, prefix: str, member_id: str) -> None:
    listing = f'/{COLLECTION}/{carrier_id}/{prefix}'
    invalidate([listing, f'{listing}/{member_id}'])


def staled_list(carrier_id: str, prefix: str) -> None:
    listing = f'/{COLLECTION}/{carrier_id}/{prefix}'
    invalidate([listing, f'{listing}/*'])


def named(event: Dict[str, Any]) -> Optional[str]:
    body = parse_fields(event, ('name',))
    if body is None:
        return None
    name = body['name']
    return name if isinstance(name, str) and name else None


def pop(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': sort_id(item),
        'municipality': item['municipality']['S'],
        'state': item['state']['S'],
        'country': item['country']['S'],
        'latitude': float(item['latitude']['N']),
        'longitude': float(item['longitude']['N']),
    }


def fiber_segment(item: Dict[str, Any]) -> Dict[str, Any]:
    ends = {field: item[field]['S'] for field in ENDS}
    return {'id': sort_id(item), **ends, SUBMARINE: item[SUBMARINE]['BOOL']}


Row = Callable[[Dict[str, Any]], Dict[str, Any]]


def list_under(event: Dict[str, Any], prefix: str, row: Row, failure: str) -> Dict[str, Any]:
    carrier_id = requested(event)
    if carrier_id is None:
        return error_response(404, MISSING)
    try:
        stored = held(COLLECTION, carrier_id)
        table = os.environ['STORE_TABLE']
        items = partition(table, f'{COLLECTION}/{carrier_id}', f'{prefix}/') if stored else []
    except ClientError as error:
        logger.error('Error reading the %s of carrier %s: %s', prefix, carrier_id, error)
        return error_response(500, failure)
    if stored is None:
        return error_response(404, MISSING)
    return json_response(200, sorted(map(row, items), key=lambda one: one['id']))


def counted(
    take: Callable[..., int], carrier_id: str, *taking: Any, **request: Any
) -> Optional[int]:
    try:
        return take(
            os.environ['STORE_TABLE'], {'PK': {'S': COLLECTION}, 'SK': {'S': carrier_id}}, *taking,
            ConditionExpression='attribute_exists(PK)', **request,
        )
    except ClientError as error:
        if conditional(error):
            return None
        raise


def next_under(carrier_id: str, counter: str) -> Optional[int]:
    return counted(reserve, carrier_id, counter, 1)


def located(body: Dict[str, Any]) -> bool:
    return has_strings(body, PLACE, NAMED) and has_numbers(body, COORDINATES)


def spanning(body: Dict[str, Any]) -> bool:
    return has_strings(body, ENDS, SPANNED) and isinstance(body[SUBMARINE], bool)


def pop_attributes(body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **{field: {'S': body[field]} for field in PLACE},
        **{field: {'N': str(body[field])} for field in COORDINATES},
    }


def fiber_segment_attributes(body: Dict[str, Any]) -> Dict[str, Any]:
    return {**{field: {'S': body[field]} for field in ENDS}, SUBMARINE: {'BOOL': body[SUBMARINE]}}


def put_under(
    carrier_id: str, prefix: str, member_id: str, attributes: Dict[str, Any], **request: Any
) -> Dict[str, Any]:
    table = os.environ['STORE_TABLE']
    return put(table, f'{COLLECTION}/{carrier_id}', f'{prefix}/{member_id}', attributes, **request)


Attributes = Callable[[Dict[str, Any]], Dict[str, Any]]


class Kind(NamedTuple):
    prefix: str
    parameter: str
    missing: str
    counter: str
    fields: Tuple[str, ...]
    valid: Valid
    refusal: str
    list_refusal: str
    attributes: Attributes
    row: Row
    failure: str


POP_KIND = Kind(
    POPS, 'pop_id', MISSING_POP, 'next_pop', PLACE + COORDINATES, located, POP_BODY, POPS_BODY,
    pop_attributes, pop, 'Failed to add the pop',
)
FIBER_SEGMENT_KIND = Kind(
    FIBER_SEGMENTS, 'fiber_segment_id', MISSING_FIBER_SEGMENT, 'next_fiber_segment',
    ENDS + (SUBMARINE,), spanning, FIBER_SEGMENT_BODY, FIBER_SEGMENTS_BODY,
    fiber_segment_attributes, fiber_segment, 'Failed to add the fiber segment',
)


def body_of(event: Dict[str, Any], kind: Kind) -> Optional[Dict[str, Any]]:
    return parse_valid(event, kind.fields, kind.valid)


def fits(one: Any, kind: Kind) -> bool:
    return isinstance(one, dict) and set(one) == set(kind.fields) and kind.valid(one)


def bodies_of(event: Dict[str, Any], kind: Kind) -> Optional[List[Dict[str, Any]]]:
    try:
        bodies = parse_body(event)
    except ValueError:
        return None
    if not isinstance(bodies, list) or not all(fits(one, kind) for one in bodies):
        return None
    listed: List[Dict[str, Any]] = bodies
    return listed


def add_under(event: Dict[str, Any], kind: Kind) -> Dict[str, Any]:
    body = body_of(event, kind)
    if body is None:
        return error_response(400, kind.refusal)
    carrier_id = requested(event)
    if carrier_id is None:
        return error_response(404, MISSING)
    try:
        member_id = next_under(carrier_id, kind.counter)
        item = (
            put_under(carrier_id, kind.prefix, str(member_id), kind.attributes(body))
            if member_id is not None else None
        )
    except ClientError as error:
        logger.error('Error adding to the %s of carrier %s: %s', kind.prefix, carrier_id, error)
        return error_response(500, kind.failure)
    if item is None:
        return error_response(404, MISSING)
    staled_under(carrier_id, kind.prefix, str(member_id))
    return created(f'/{COLLECTION}/{carrier_id}/{kind.prefix}/{member_id}', kind.row(item))


Act = Callable[[str, str], Optional[Dict[str, Any]]]
Answer = Callable[[Dict[str, Any]], Dict[str, Any]]


def on_member(
    event: Dict[str, Any], kind: Kind, act: Act, failure: str, answer: Optional[Answer] = None
) -> Dict[str, Any]:
    carrier_id = requested(event)
    if carrier_id is None:
        return error_response(404, MISSING)
    member_id = path_id(event, kind.parameter)
    if member_id is None:
        return error_response(404, kind.missing)
    try:
        stored = held(COLLECTION, carrier_id)
        item = act(carrier_id, member_id) if stored else None
    except ClientError as error:
        logger.error(
            'Error with %s/%s of carrier %s: %s', kind.prefix, member_id, carrier_id, error
        )
        return error_response(500, failure)
    if stored is None:
        return error_response(404, MISSING)
    if item is None:
        return error_response(404, kind.missing)
    return answer(item) if answer else json_response(200, kind.row(item))


def stored_under(carrier_id: str, member_id: str, prefix: str) -> Optional[Dict[str, Any]]:
    return held(f'{COLLECTION}/{carrier_id}', f'{prefix}/{member_id}')


def read_under(event: Dict[str, Any], kind: Kind, failure: str) -> Dict[str, Any]:
    return on_member(event, kind, partial(stored_under, prefix=kind.prefix), failure)


def staling(act: Act, prefix: str) -> Act:
    def acting(carrier_id: str, member_id: str) -> Optional[Dict[str, Any]]:
        item = act(carrier_id, member_id)
        if item is not None:
            staled_under(carrier_id, prefix, member_id)
        return item
    return acting


def replace_under(
    carrier_id: str, member_id: str, kind: Kind, body: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    try:
        return put_under(
            carrier_id, kind.prefix, member_id, kind.attributes(body),
            ConditionExpression='attribute_exists(PK)',
        )
    except ClientError as error:
        if conditional(error):
            return None
        raise


def update_under(event: Dict[str, Any], kind: Kind, failure: str) -> Dict[str, Any]:
    body = body_of(event, kind)
    if body is None:
        return error_response(400, kind.refusal)
    replaced = staling(partial(replace_under, kind=kind, body=body), kind.prefix)
    return on_member(event, kind, replaced, failure)


def remove_under(carrier_id: str, member_id: str, prefix: str) -> Optional[Dict[str, Any]]:
    table = os.environ['STORE_TABLE']
    return delete(table, f'{COLLECTION}/{carrier_id}', f'{prefix}/{member_id}')


def delete_under(event: Dict[str, Any], kind: Kind, failure: str) -> Dict[str, Any]:
    removed = staling(partial(remove_under, prefix=kind.prefix), kind.prefix)
    return on_member(event, kind, removed, failure, lambda _gone: no_content())


def relisted(
    carrier_id: str, kind: Kind, first: int, bodies: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    table = os.environ['STORE_TABLE']
    holder = f'{COLLECTION}/{carrier_id}'
    items = [
        {'PK': {'S': holder}, 'SK': {'S': f'{kind.prefix}/{first + index}'}, **kind.attributes(one)}
        for index, one in enumerate(bodies)
    ]
    stale = partition(table, holder, f'{kind.prefix}/')
    batch_write(table, [
        *({'DeleteRequest': {'Key': {'PK': item['PK'], 'SK': item['SK']}}} for item in stale),
        *({'PutRequest': {'Item': item}} for item in items),
    ])
    return items


def replace_list_under(event: Dict[str, Any], kind: Kind, failure: str) -> Dict[str, Any]:
    bodies = bodies_of(event, kind)
    if bodies is None:
        return error_response(400, kind.list_refusal)
    carrier_id = requested(event)
    if carrier_id is None:
        return error_response(404, MISSING)
    try:
        first = counted(reserve, carrier_id, kind.counter, len(bodies))
        items = relisted(carrier_id, kind, first, bodies) if first is not None else None
    except ClientError as error:
        logger.error('Error replacing the %s of carrier %s: %s', kind.prefix, carrier_id, error)
        return error_response(500, failure)
    if items is None:
        return error_response(404, MISSING)
    staled_list(carrier_id, kind.prefix)
    return json_response(200, [kind.row(item) for item in items])
