from functools import partial
from typing import Any, Dict

from lambda_http import dispatch
from syntheses import FORCED_HOMES, list_under, listed

_list = partial(list_under, part=FORCED_HOMES, failure='Failed to read the forced homes')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(listed(FORCED_HOMES), 'GET'): _list})
