from functools import partial
from typing import Any, Dict

from lambda_http import dispatch
from syntheses import DEGREE_EXEMPT_WAN_POPS, list_under, listed

_list = partial(
    list_under, part=DEGREE_EXEMPT_WAN_POPS, failure='Failed to read the degree-exempt wan pops'
)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(listed(DEGREE_EXEMPT_WAN_POPS), 'GET'): _list})
