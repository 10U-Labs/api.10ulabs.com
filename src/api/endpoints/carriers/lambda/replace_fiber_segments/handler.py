from functools import partial
from typing import Any, Dict

from carriers import FIBER_SEGMENT_KIND, replace_list_under
from lambda_http import dispatch

_replace = partial(
    replace_list_under, kind=FIBER_SEGMENT_KIND, failure='Failed to replace the fiber segments'
)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {('/carriers/{id}/fiber-segments', 'PUT'): _replace})
