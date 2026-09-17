from functools import partial
from typing import Any, Dict

from lambda_http import dispatch
from syntheses import FORCED_WAN_POPS, list_under, listed

_list = partial(list_under, part=FORCED_WAN_POPS, failure='Failed to read the forced wan pops')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(listed(FORCED_WAN_POPS), 'GET'): _list})
