from functools import partial
from typing import Any, Dict

from lambda_http import dispatch
from syntheses import SITES, read_under, one

_read = partial(read_under, part=SITES, failure='Failed to read the site')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(one(SITES), 'GET'): _read})
