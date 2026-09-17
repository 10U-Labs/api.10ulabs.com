from functools import partial
from typing import Any, Dict

from lambda_http import dispatch
from syntheses import FORCED_CIRCUITS, list_under, listed

_list = partial(list_under, part=FORCED_CIRCUITS, failure='Failed to read the forced circuits')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(listed(FORCED_CIRCUITS), 'GET'): _list})
