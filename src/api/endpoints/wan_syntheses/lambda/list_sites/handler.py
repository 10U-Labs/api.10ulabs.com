from functools import partial
from typing import Any, Dict

from lambda_http import dispatch
from syntheses import SITES, list_under, listed

_list = partial(list_under, part=SITES, failure='Failed to read the sites')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(listed(SITES), 'GET'): _list})
