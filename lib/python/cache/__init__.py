import logging
import os
import uuid
from typing import Iterable

from botocore.exceptions import ClientError

from lambda_http import aws_client

logger = logging.getLogger()


def invalidate(paths: Iterable[str]) -> None:
    listed = list(paths)
    try:
        aws_client('cloudfront').create_invalidation(
            DistributionId=os.environ['DISTRIBUTION_ID'],
            InvalidationBatch={
                'Paths': {'Quantity': len(listed), 'Items': listed},
                'CallerReference': str(uuid.uuid4()),
            },
        )
    except ClientError as error:
        logger.error('Error invalidating %s: %s', listed, error)
