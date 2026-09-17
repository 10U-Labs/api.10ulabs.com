from functools import partial
from typing import Any, Dict

from lambda_http import dispatch
from syntheses import PROHIBITED_WAN_POPS, list_under, listed

_list = partial(
    list_under, part=PROHIBITED_WAN_POPS, failure='Failed to read the prohibited wan pops'
)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(listed(PROHIBITED_WAN_POPS), 'GET'): _list})
