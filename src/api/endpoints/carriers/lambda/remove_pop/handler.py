from functools import partial
from typing import Any, Dict

from carriers import POP_KIND, delete_under
from lambda_http import dispatch

REMOVE = partial(delete_under, kind=POP_KIND, failure='Failed to delete the pop')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {('/carriers/{id}/pops/{pop_id}', 'DELETE'): REMOVE})
