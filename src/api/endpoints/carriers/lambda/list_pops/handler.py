from functools import partial
from typing import Any, Dict

from carriers import POPS, list_under, pop
from lambda_http import dispatch

LIST = partial(list_under, prefix=POPS, row=pop, failure='Failed to read the pops')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {('/carriers/{id}/pops', 'GET'): LIST})
