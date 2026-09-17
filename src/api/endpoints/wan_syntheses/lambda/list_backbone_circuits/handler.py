from functools import partial
from typing import Any, Dict

from lambda_http import dispatch
from syntheses import BACKBONE_CIRCUITS, list_under, listed

_list = partial(list_under, part=BACKBONE_CIRCUITS, failure='Failed to read the backbone circuits')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(listed(BACKBONE_CIRCUITS), 'GET'): _list})
