from functools import partial
from typing import Any, Dict

from carriers import POP_KIND, update_under
from lambda_http import dispatch

CORRECT = partial(update_under, kind=POP_KIND, failure='Failed to update the pop')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {('/carriers/{id}/pops/{pop_id}', 'PUT'): CORRECT})
