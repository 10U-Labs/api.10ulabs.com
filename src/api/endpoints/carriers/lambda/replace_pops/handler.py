from functools import partial
from typing import Any, Dict

from carriers import POP_KIND, replace_list_under
from lambda_http import dispatch

_replace = partial(replace_list_under, kind=POP_KIND, failure='Failed to replace the pops')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {('/carriers/{id}/pops', 'PUT'): _replace})
