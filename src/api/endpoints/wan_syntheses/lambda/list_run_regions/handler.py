from functools import partial
from typing import Any, Dict

from lambda_http import dispatch
from syntheses import REGIONS, list_under, listed

_list = partial(
    list_under, part=REGIONS, failure='Failed to read the hyperscale cloud service provider regions'
)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(listed(REGIONS), 'GET'): _list})
