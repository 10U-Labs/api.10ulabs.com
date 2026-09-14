import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from botocore.exceptions import ClientError

from lambda_http import aws_client, dispatch, json_response, parse_object

logger = logging.getLogger()
logger.setLevel(logging.INFO)

HASH_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
HASH_LENGTH = 9
RACK_HEIGHT_MAXIMUM = 42
CONFIGURATION_HASH = re.compile(r'^[0-9A-Z]{9}$')
CORS_HEADERS = {'Access-Control-Allow-Origin': '*'}


def _error(status_code: int, message: str) -> Dict[str, Any]:
    return json_response(status_code, {'success': False, 'error': message})


def configuration_hash(configuration: Dict[str, Any]) -> str:
    canonical = json.dumps(configuration, sort_keys=True, separators=(',', ':'))
    remaining = int.from_bytes(hashlib.sha256(canonical.encode('utf-8')).digest()[:6], 'big')
    characters = []
    for _ in range(HASH_LENGTH):
        characters.append(HASH_ALPHABET[remaining % len(HASH_ALPHABET)])
        remaining //= len(HASH_ALPHABET)
    return ''.join(characters)


def _validation_error(configuration: Dict[str, Any]) -> Optional[str]:
    for field in ('rackHeight', 'rackCount', 'placedParts'):
        if field not in configuration:
            return f'Missing required field: {field}'
    for field in ('rackHeight', 'rackCount'):
        if not isinstance(configuration[field], int) or isinstance(configuration[field], bool):
            return f'{field} must be an integer'
    if not isinstance(configuration['placedParts'], list):
        return 'placedParts must be an array'
    if not 1 <= configuration['rackHeight'] <= RACK_HEIGHT_MAXIMUM:
        return f'rackHeight must be between 1 and {RACK_HEIGHT_MAXIMUM}'
    if configuration['rackCount'] < 1:
        return 'rackCount must be at least 1'
    return None


def _store(config_hash: str, configuration: Dict[str, Any], device_id: str) -> None:
    item = {
        'config_hash': {'S': config_hash},
        'configuration': {'S': json.dumps(configuration)},
        'created_at': {'S': datetime.now(timezone.utc).isoformat()},
        'device_id': {'S': device_id},
    }
    try:
        aws_client('dynamodb').put_item(
            TableName=os.environ['RACK_CONFIGURATIONS_TABLE'],
            Item=item,
            ConditionExpression='attribute_not_exists(config_hash)'
        )
    except ClientError as error:
        if error.response['Error']['Code'] != 'ConditionalCheckFailedException':
            raise
        logger.info('Configuration already stored: %s', config_hash)


def _create(event: Dict[str, Any]) -> Dict[str, Any]:
    body = parse_object(event)
    if body is None:
        return _error(400, 'Invalid JSON')
    device_id = body.get('device_id')
    configuration = body.get('configuration')
    if not device_id:
        return _error(400, 'Missing required field: device_id')
    if not isinstance(configuration, dict) or not configuration:
        return _error(400, 'Missing required field: configuration')
    validation_error = _validation_error(configuration)
    if validation_error:
        return _error(400, validation_error)
    config_hash = configuration_hash(configuration)
    try:
        _store(config_hash, configuration, str(device_id))
    except ClientError as error:
        logger.error('Error storing rack configuration: %s', error)
        return _error(500, 'Failed to store the configuration')
    return json_response(200, {'success': True, 'config_hash': config_hash})


def _read(event: Dict[str, Any]) -> Dict[str, Any]:
    config_hash = (event.get('pathParameters') or {}).get('config_hash') or ''
    if not CONFIGURATION_HASH.match(config_hash):
        return _error(400, 'Invalid config_hash format')
    try:
        item = aws_client('dynamodb').get_item(
            TableName=os.environ['RACK_CONFIGURATIONS_TABLE'],
            Key={'config_hash': {'S': config_hash}}
        ).get('Item')
    except ClientError as error:
        logger.error('Error reading rack configuration: %s', error)
        return _error(500, 'Failed to read the configuration')
    if not item:
        return _error(404, 'Configuration not found')
    configuration = json.loads(item['configuration']['S'])
    return json_response(
        200, {'success': True, 'config_hash': config_hash, 'configuration': configuration}
    )


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    response = dispatch(event, {
        ('/rack-configurations', 'POST'): _create,
        ('/rack-configurations/{config_hash}', 'GET'): _read,
    })
    response['headers'].update(CORS_HEADERS)
    return response
