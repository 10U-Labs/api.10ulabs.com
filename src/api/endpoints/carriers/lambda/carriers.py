import logging
import os
from typing import Any, Dict, Optional

from lambda_http import parse_fields, path_id
from store import member, sort_id

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COLLECTION = 'carriers'
BODY = 'The body must be exactly {"name"}'
MISSING = 'No such carrier'


def carrier(item: Dict[str, Any]) -> Dict[str, Any]:
    return {'id': sort_id(item), 'name': item['name']['S']}


def requested(event: Dict[str, Any]) -> Optional[str]:
    return path_id(event, 'id')


def held(collection: str, member_id: str) -> Optional[Dict[str, Any]]:
    return member(os.environ['STORE_TABLE'], collection, member_id)


def named(event: Dict[str, Any]) -> Optional[str]:
    body = parse_fields(event, ('name',))
    if body is None:
        return None
    name = body['name']
    return name if isinstance(name, str) and name else None
