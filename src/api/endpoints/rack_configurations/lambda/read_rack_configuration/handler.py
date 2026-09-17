import json
import os
from typing import Any, Dict

from botocore.exceptions import ClientError

from lambda_http import aws_client, json_response
from rack_configurations import CONFIGURATION_HASH, MEMBER, error, logger, served


def _read(event: Dict[str, Any]) -> Dict[str, Any]:
    config_hash = (event.get('pathParameters') or {}).get('id') or ''
    if not CONFIGURATION_HASH.match(config_hash):
        return error(400, 'Invalid config_hash format')
    try:
        item = aws_client('dynamodb').get_item(
            TableName=os.environ['RACK_CONFIGURATIONS_TABLE'],
            Key={'config_hash': {'S': config_hash}}
        ).get('Item')
    except ClientError as failure:
        logger.error('Error reading rack configuration: %s', failure)
        return error(500, 'Failed to read the configuration')
    if not item:
        return error(404, 'Configuration not found')
    configuration = json.loads(item['configuration']['S'])
    return json_response(
        200, {'success': True, 'config_hash': config_hash, 'configuration': configuration}
    )


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    return served(event, {(MEMBER, 'GET'): _read})
