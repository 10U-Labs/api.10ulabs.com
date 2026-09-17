from functools import partial
from typing import Any, Dict

from carriers import FIBER_SEGMENT_KIND, delete_under
from lambda_http import dispatch

_remove = partial(
    delete_under, kind=FIBER_SEGMENT_KIND, failure='Failed to delete the fiber segment'
)
MEMBER = '/carriers/{id}/fiber-segments/{fiber_segment_id}'


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(MEMBER, 'DELETE'): _remove})
