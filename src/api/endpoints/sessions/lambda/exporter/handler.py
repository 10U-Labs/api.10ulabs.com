import os
from datetime import datetime, timezone
from typing import Any, Dict

import boto3


def lambda_handler(_event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    bucket = os.environ['S3_BUCKET']
    prefix = f"{os.environ['S3_PREFIX']}/{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S')}"
    export = boto3.client('dynamodb').export_table_to_point_in_time(
        TableArn=os.environ['DYNAMODB_TABLE_ARN'],
        S3Bucket=bucket,
        S3Prefix=prefix,
        ExportFormat='DYNAMODB_JSON'
    )
    return {
        'statusCode': 200,
        'body': {
            'export_arn': export['ExportDescription']['ExportArn'],
            's3_path': f's3://{bucket}/{prefix}'
        }
    }
