from functools import partial
from typing import Any, Dict

from carriers import FIBER_SEGMENTS, fiber_segment, list_under
from lambda_http import dispatch

_list = partial(
    list_under, prefix=FIBER_SEGMENTS, row=fiber_segment,
    failure='Failed to read the fiber segments',
)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {('/carriers/{id}/fiber-segments', 'GET'): _list})
