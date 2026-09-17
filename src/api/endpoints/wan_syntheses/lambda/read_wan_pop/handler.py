from functools import partial
from typing import Any, Dict

from lambda_http import dispatch
from syntheses import WAN_POPS, read_under, one

_read = partial(read_under, part=WAN_POPS, failure='Failed to read the wan pop')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(one(WAN_POPS), 'GET'): _read})
