import hashlib
import json
import logging
import re
from typing import Any, Dict, Mapping

from lambda_http import Handler, Route, dispatch, json_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

HASH_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
HASH_LENGTH = 9
CONFIGURATION_HASH = re.compile(r'^[0-9A-Z]{9}$')
CORS_HEADERS = {'Access-Control-Allow-Origin': '*'}
COLLECTION = '/rack-configurations'
MEMBER = f'{COLLECTION}/{{id}}'


def error(status_code: int, message: str) -> Dict[str, Any]:
    return json_response(status_code, {'success': False, 'error': message})


def configuration_hash(configuration: Dict[str, Any]) -> str:
    canonical = json.dumps(configuration, sort_keys=True, separators=(',', ':'))
    remaining = int.from_bytes(hashlib.sha256(canonical.encode('utf-8')).digest()[:6], 'big')
    characters = []
    for _ in range(HASH_LENGTH):
        characters.append(HASH_ALPHABET[remaining % len(HASH_ALPHABET)])
        remaining //= len(HASH_ALPHABET)
    return ''.join(characters)


def served(event: Dict[str, Any], routes: Mapping[Route, Handler]) -> Dict[str, Any]:
    response = dispatch(event, routes)
    response['headers'].update(CORS_HEADERS)
    return response
