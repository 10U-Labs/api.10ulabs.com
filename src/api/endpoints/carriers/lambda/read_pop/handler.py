from functools import partial
from typing import Any, Dict

from carriers import POP_KIND, read_under
from lambda_http import dispatch

_read = partial(read_under, kind=POP_KIND, failure='Failed to read the pop')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {('/carriers/{id}/pops/{pop_id}', 'GET'): _read})
