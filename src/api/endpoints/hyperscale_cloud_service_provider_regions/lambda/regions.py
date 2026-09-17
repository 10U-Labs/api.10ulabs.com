import logging
from typing import Any, Dict, Optional

from lambda_http import has_numbers, has_strings, parse_valid
from store import sort_id

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COLLECTION = 'hyperscale-cloud-service-provider-regions'
ROUTE = f'/{COLLECTION}'
MEMBER = f'{ROUTE}/{{id}}'
WORDED = ('name', 'municipality', 'state', 'country')
NAMED = ('name', 'municipality', 'country')
COORDINATES = ('latitude', 'longitude')
MISSING = 'No such hyperscale cloud service provider region'
REGION_BODY = (
    'The body must be exactly '
    '{"name", "municipality", "state", "country", "latitude", "longitude"}'
)


def region(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': sort_id(item),
        **{field: item[field]['S'] for field in WORDED},
        **{field: float(item[field]['N']) for field in COORDINATES},
    }


def region_body(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return parse_valid(
        event, WORDED + COORDINATES,
        lambda body: has_strings(body, WORDED, NAMED) and has_numbers(body, COORDINATES),
    )


def attributes(body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **{field: {'S': body[field]} for field in WORDED},
        **{field: {'N': str(body[field])} for field in COORDINATES},
    }
