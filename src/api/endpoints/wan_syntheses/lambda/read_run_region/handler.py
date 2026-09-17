from functools import partial
from typing import Any, Dict

from lambda_http import dispatch
from syntheses import REGIONS, read_under, one

_read = partial(
    read_under, part=REGIONS, failure='Failed to read the hyperscale cloud service provider region'
)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(one(REGIONS), 'GET'): _read})
