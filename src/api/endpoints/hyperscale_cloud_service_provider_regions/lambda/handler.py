import logging
import os
from typing import Any, Dict

from botocore.exceptions import ClientError

from lambda_http import dispatch, json_response
from store import members

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COLLECTION = 'hyperscale-cloud-service-provider-regions'
WORDED = ('name', 'municipality', 'state', 'country')
COORDINATES = ('latitude', 'longitude')


def _region(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': int(item['SK']['S']),
        **{field: item[field]['S'] for field in WORDED},
        **{field: float(item[field]['N']) for field in COORDINATES},
    }


def _list(_event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        regions = members(os.environ['STORE_TABLE'], COLLECTION)
    except ClientError as error:
        logger.error('Error reading the hyperscale cloud service provider regions: %s', error)
        return json_response(
            500, {'error': 'Failed to read the hyperscale cloud service provider regions'}
        )
    return json_response(200, sorted(map(_region, regions), key=lambda region: region['id']))


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {
        (f'/{COLLECTION}', 'GET'): _list,
    })
