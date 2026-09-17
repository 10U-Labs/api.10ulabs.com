from functools import partial
from typing import Any, Dict, Optional

from carriers import (
    Kind, add_under, delete_under, list_under, put_under, read_under, update_under,
)
from lambda_http import dispatch, has_strings, parse_valid
from store import sort_id

MISSING_FIBER_SEGMENT = 'No such fiber segment'
FIBER_SEGMENTS = 'fiber-segments'
ENDS = ('a_municipality', 'a_state', 'z_municipality', 'z_state')
SPANNED = ('a_municipality', 'z_municipality')
SUBMARINE = 'submarine'
FIBER_SEGMENT_BODY = (
    'The body must be exactly '
    '{"a_municipality", "a_state", "z_municipality", "z_state", "submarine"}'
)


def _fiber_segment(item: Dict[str, Any]) -> Dict[str, Any]:
    ends = {field: item[field]['S'] for field in ENDS}
    return {'id': sort_id(item), **ends, SUBMARINE: item[SUBMARINE]['BOOL']}


def _fiber_segment_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return parse_valid(
        event, ENDS + (SUBMARINE,),
        lambda body: has_strings(body, ENDS, SPANNED) and isinstance(body[SUBMARINE], bool),
    )


def _put_fiber_segment(
    carrier_id: str, segment_id: str, body: Dict[str, Any], **request: Any
) -> Dict[str, Any]:
    return put_under(carrier_id, FIBER_SEGMENTS, segment_id, {
        **{field: {'S': body[field]} for field in ENDS},
        SUBMARINE: {'BOOL': body[SUBMARINE]},
    }, **request)


FIBER_SEGMENT_KIND = Kind(
    FIBER_SEGMENTS, 'fiber_segment_id', MISSING_FIBER_SEGMENT, 'next_fiber_segment',
    _fiber_segment_body, FIBER_SEGMENT_BODY, _put_fiber_segment, _fiber_segment,
    'Failed to add the fiber segment',
)
ROUTE = '/carriers/{id}/fiber-segments'
MEMBER = f'{ROUTE}/{{fiber_segment_id}}'


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {
        (ROUTE, 'GET'): partial(
            list_under, prefix=FIBER_SEGMENTS, row=_fiber_segment,
            failure='Failed to read the fiber segments',
        ),
        (ROUTE, 'POST'): partial(add_under, kind=FIBER_SEGMENT_KIND),
        (MEMBER, 'GET'): partial(
            read_under, kind=FIBER_SEGMENT_KIND, failure='Failed to read the fiber segment'
        ),
        (MEMBER, 'PUT'): partial(
            update_under, kind=FIBER_SEGMENT_KIND, failure='Failed to update the fiber segment'
        ),
        (MEMBER, 'DELETE'): partial(
            delete_under, kind=FIBER_SEGMENT_KIND, failure='Failed to delete the fiber segment'
        ),
    })
