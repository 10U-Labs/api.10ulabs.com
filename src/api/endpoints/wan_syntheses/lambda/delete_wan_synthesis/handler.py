import logging
import os
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError

from lambda_http import dispatch, error_response, no_content, path_id
from store import member, remove

logger = logging.getLogger()
logger.setLevel(logging.INFO)

COLLECTION = 'wan-syntheses'
MISSING = 'No such wan synthesis'
RUNNING = ('creating', 'synthesizing')


def _removed(table: str, synthesis_id: Optional[str]) -> Dict[str, Any]:
    record = None if synthesis_id is None else member(table, COLLECTION, synthesis_id)
    if record is None or synthesis_id is None:
        return error_response(404, MISSING)
    if record['status']['S'] in RUNNING:
        return error_response(409, 'The synthesis is still running')
    if not remove(table, COLLECTION, synthesis_id):
        return error_response(404, MISSING)
    return no_content()


def _delete(event: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return _removed(os.environ['STORE_TABLE'], path_id(event, 'id'))
    except ClientError as error:
        logger.error('Error deleting a wan synthesis: %s', error)
        return error_response(500, 'Failed to delete the wan synthesis')


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return dispatch(event, {(f'/{COLLECTION}/{{id}}', 'DELETE'): _delete})
