from functools import partial
from typing import Any, Dict

from lambda_http import dispatch
from syntheses import FIBER_SEGMENTS, list_under, listed

_list = partial(list_under, part=FIBER_SEGMENTS, failure='Failed to read the fiber segments')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(listed(FIBER_SEGMENTS), 'GET'): _list})
