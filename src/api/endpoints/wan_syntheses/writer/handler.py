import json
import logging
import os
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple

from botocore.exceptions import ClientError

from lambda_http import (
    aws_client, created, dispatch, error_response, has_numbers, has_strings, no_content,
    parse_fields, path_id,
)
from store import member, next_id, put, remove, typed

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COLLECTION = 'wan-syntheses'
MISSING = 'No such wan synthesis'
RUNNING = ('creating', 'synthesizing')
SCALARS = (
    'label', 'wan_pop_count', 'backbone_number_of_diverse_circuits', 'homing_degree',
    'convergence_promotion', 'knobs', 'settings',
)
PLACE = ('municipality', 'state', 'country')
COORDINATES = ('latitude', 'longitude')
ENDS = ('source', 'target')


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _object(value: Any, fields: Tuple[str, ...]) -> bool:
    return isinstance(value, dict) and set(value) == set(fields)


def _placed(element: Any, named: Tuple[str, ...] = (), flagged: Tuple[str, ...] = ()) -> bool:
    fields = named + PLACE + COORDINATES + flagged
    return (
        _object(element, fields)
        and has_strings(element, named + PLACE, named + ('municipality', 'country'))
        and has_numbers(element, COORDINATES)
        and all(isinstance(element[field], bool) for field in flagged)
    )


def _named(element: Any) -> bool:
    return isinstance(element, str) and bool(element)


def _ended(element: Any) -> bool:
    return _object(element, ENDS) and has_strings(element, ENDS, ENDS)


class ListInput(NamedTuple):
    field: str
    prefix: str
    valid: Callable[[Any], bool]
    attributes: Callable[[Any], Dict[str, Any]]


def _as_given(element: Dict[str, Any]) -> Dict[str, Any]:
    return dict(element)


def _region_attributes(element: Dict[str, Any]) -> Dict[str, Any]:
    return {field: element[field] for field in ('name',) + PLACE + COORDINATES}


def _name_attributes(element: str) -> Dict[str, Any]:
    return {'name': element}


LIST_INPUTS = (
    ListInput(
        'sites', 'sites', lambda one: _placed(one, ('name',), ('exempt_from_distance_constraint',)),
        _as_given,
    ),
    ListInput(
        'hyperscale_cloud_service_provider_regions', 'hyperscale-cloud-service-provider-regions',
        lambda one: isinstance(one, dict) and _placed(
            {field: value for field, value in one.items() if field != 'id'}, ('name',)
        ),
        _region_attributes,
    ),
    ListInput('off_net', 'off-net', _placed, _as_given),
    ListInput('forced_wan_pops', 'forced-wan-pops', _named, _name_attributes),
    ListInput('forced_circuits', 'forced-circuits', _ended, _as_given),
    ListInput('forced_homes', 'forced-homes', _ended, _as_given),
    ListInput('prohibited_wan_pops', 'prohibited-wan-pops', _named, _name_attributes),
    ListInput('prohibited_circuits', 'prohibited-circuits', _ended, _as_given),
    ListInput('degree_exempt_wan_pops', 'degree-exempt-wan-pops', _named, _name_attributes),
)
FIELDS = SCALARS + tuple(one.field for one in LIST_INPUTS)
BODY = "The body must be exactly the run's " + ', '.join(FIELDS)
SCALAR_VALIDITY: Dict[str, Callable[[Any], bool]] = {
    'label': _named,
    'wan_pop_count': lambda value: _object(value, ('min', 'max')) and all(
        _integer(value[bound]) for bound in ('min', 'max')
    ),
    'backbone_number_of_diverse_circuits': _integer,
    'homing_degree': _integer,
    'convergence_promotion': lambda value: isinstance(value, bool),
    'knobs': lambda value: isinstance(value, dict),
    'settings': lambda value: isinstance(value, dict),
}


def _invalid(body: Dict[str, Any]) -> Optional[str]:
    for field, valid in SCALAR_VALIDITY.items():
        if not valid(body[field]):
            return field
    for one in LIST_INPUTS:
        elements = body[one.field]
        if not isinstance(elements, list) or not all(one.valid(element) for element in elements):
            return one.field
    return None


def _record(synthesis_id: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {'id': synthesis_id, **{field: body[field] for field in SCALARS}, 'status': 'creating'}


def _write(table: str, body: Dict[str, Any]) -> int:
    synthesis_id = next_id(table, COLLECTION)
    record = _record(synthesis_id, body)
    put(table, COLLECTION, str(synthesis_id), {
        field: typed(value) for field, value in record.items() if field != 'id'
    })
    under = f'{COLLECTION}/{synthesis_id}'
    for one in LIST_INPUTS:
        elements: List[Any] = body[one.field]
        for position, element in enumerate(elements, start=1):
            attributes = one.attributes(element)
            put(table, under, f'{one.prefix}/{position}', {
                field: typed(value) for field, value in attributes.items()
            })
    return synthesis_id


def _create(event: Dict[str, Any]) -> Dict[str, Any]:
    body = parse_fields(event, FIELDS)
    if body is None:
        return error_response(400, BODY)
    invalid = _invalid(body)
    if invalid is not None:
        return error_response(400, f'Invalid {invalid}')
    try:
        synthesis_id = _write(os.environ['STORE_TABLE'], body)
    except ClientError as error:
        logger.error('Error creating the wan synthesis: %s', error)
        return error_response(500, 'Failed to create the wan synthesis')
    try:
        aws_client('lambda').invoke(
            FunctionName=os.environ['SYNTHESIZER'], InvocationType='Event',
            Payload=json.dumps({'synthesis': synthesis_id}),
        )
    except ClientError as error:
        logger.error('Error starting synthesis %s: %s', synthesis_id, error)
        return error_response(500, 'Failed to start the synthesis')
    return created(f'/{COLLECTION}/{synthesis_id}', _record(synthesis_id, body))


def _removed(table: str, synthesis_id: Optional[str]) -> Dict[str, Any]:
    record = None if synthesis_id is None else member(table, COLLECTION, synthesis_id)
    if record is None or synthesis_id is None:
        return error_response(404, MISSING)
    if record['status']['S'] in RUNNING:
        return error_response(409, 'The synthesis is still running')
    if not remove(table, COLLECTION, synthesis_id):
        return error_response(404, MISSING)
    return no_content()


def _delete(event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return _removed(os.environ['STORE_TABLE'], path_id(event, 'synthesis'))
    except ClientError as error:
        logger.error('Error deleting a wan synthesis: %s', error)
        return error_response(500, 'Failed to delete the wan synthesis')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {
        (f'/{COLLECTION}', 'POST'): _create,
        (f'/{COLLECTION}/{{synthesis}}', 'DELETE'): _delete,
    })
