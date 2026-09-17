from functools import partial
from typing import Any, Dict

from lambda_http import dispatch
from syntheses import WAN_POPS, list_under, listed

_list = partial(list_under, part=WAN_POPS, failure='Failed to read the wan pops')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(listed(WAN_POPS), 'GET'): _list})
