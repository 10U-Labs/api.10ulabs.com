from functools import partial
from typing import Any, Dict

from carriers import FIBER_SEGMENT_KIND, add_under
from lambda_http import dispatch

_add = partial(add_under, kind=FIBER_SEGMENT_KIND)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {('/carriers/{id}/fiber-segments', 'POST'): _add})
