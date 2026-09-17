from functools import partial
from typing import Any, Dict

from carriers import POP_KIND, add_under
from lambda_http import dispatch

ADD = partial(add_under, kind=POP_KIND)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {('/carriers/{id}/pops', 'POST'): ADD})
