from functools import partial
from typing import Any, Dict

from lambda_http import dispatch
from syntheses import OFF_NET, list_under, listed

_list = partial(list_under, part=OFF_NET, failure='Failed to read the off-net pops')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(listed(OFF_NET), 'GET'): _list})
