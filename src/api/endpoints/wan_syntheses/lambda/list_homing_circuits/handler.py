from functools import partial
from typing import Any, Dict

from lambda_http import dispatch
from syntheses import HOMING_CIRCUITS, list_under, listed

_list = partial(list_under, part=HOMING_CIRCUITS, failure='Failed to read the homing circuits')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(listed(HOMING_CIRCUITS), 'GET'): _list})
