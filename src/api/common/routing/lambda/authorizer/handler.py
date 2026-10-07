import hmac
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Tuple, Union

from lambda_http import aws_client

logger = logging.getLogger()
logger.setLevel(logging.INFO)

TOKENINFO = 'https://oauth2.googleapis.com/tokeninfo'
ISSUERS = frozenset({'accounts.google.com', 'https://accounts.google.com'})
API_KEY_PRINCIPAL = 'api-key'
WORKFLOW_WRITES: Tuple[Tuple[str, str], ...] = (
    ('POST', 'carriers'),
    ('DELETE', 'carriers/*'),
    ('POST', 'carriers/*/pops'),
    ('PUT', 'carriers/*/pops'),
    ('POST', 'carriers/*/fiber-segments'),
    ('PUT', 'carriers/*/fiber-segments'),
    ('POST', 'hyperscale-cloud-service-provider-regions'),
    ('DELETE', 'hyperscale-cloud-service-provider-regions/*'),
    ('POST', 'wan-syntheses'),
    ('DELETE', 'wan-syntheses/*'),
)

Operations = Callable[[str], Union[str, List[str]]]


class Unauthorized(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__('Unauthorized')
        self.reason = reason


def _parameter(name: str) -> str:
    parameter = aws_client('ssm').get_parameter(Name=os.environ[name], WithDecryption=True)
    return str(parameter['Parameter']['Value'])


def _authorized_accounts() -> frozenset[str]:
    listed = _parameter('AUTHORIZED_ACCOUNTS_PARAMETER').split(',')
    return frozenset(account.strip().lower() for account in listed if account.strip())


def _bearer(event: Dict[str, Any]) -> str:
    scheme, _, token = str(event.get('authorizationToken', '')).partition(' ')
    if scheme != 'Bearer' or not token:
        raise Unauthorized('no-bearer')
    return token


def _claims(token: str) -> Dict[str, Any]:
    query = urllib.parse.urlencode({'id_token': token})
    request = urllib.request.Request(f'{TOKENINFO}?{query}')
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            claims: Dict[str, Any] = json.loads(response.read())
    except urllib.error.HTTPError as refusal:
        raise Unauthorized('tokeninfo-refused') from refusal
    if claims.get('aud') != os.environ['GOOGLE_CLIENT_ID']:
        raise Unauthorized('wrong-audience')
    if claims.get('iss') not in ISSUERS:
        raise Unauthorized('wrong-issuer')
    return claims


def _admission(claims: Dict[str, Any], email: str) -> str:
    if claims.get('hd') != os.environ['HOSTED_DOMAIN']:
        return 'hosted-domain'
    if claims.get('email_verified') != 'true':
        return 'email-unverified'
    if email.lower() not in _authorized_accounts():
        return 'not-on-list'
    return 'authorized'


def _log(event: Dict[str, Any], principal: str, verdict: str, reason: str) -> None:
    logger.info(json.dumps({
        'principal': principal,
        'verdict': verdict,
        'reason': reason,
        'methodArn': event.get('methodArn'),
    }))


def _every_operation(stage: str) -> Union[str, List[str]]:
    return f'{stage}/*'


def _the_workflows_operations(stage: str) -> Union[str, List[str]]:
    reads = [f'{stage}/GET/*']
    return reads + [f'{stage}/{method}/{path}' for method, path in WORKFLOW_WRITES]


def _verdict(
    event: Dict[str, Any], principal: str, reason: str, operations: Operations
) -> Dict[str, Any]:
    effect = 'Allow' if reason in (API_KEY_PRINCIPAL, 'authorized') else 'Deny'
    _log(event, principal, effect.lower(), reason)
    api, stage_name, *_ = str(event['methodArn']).split('/')
    stage = f'{api}/{stage_name}'
    return {
        'principalId': principal,
        'policyDocument': {
            'Version': '2012-10-17',
            'Statement': [{
                'Action': 'execute-api:Invoke',
                'Effect': effect,
                'Resource': operations(stage),
            }],
        },
    }


def _decided(event: Dict[str, Any]) -> Dict[str, Any]:
    token = _bearer(event)
    if hmac.compare_digest(token.encode(), _parameter('API_KEY_PARAMETER').encode()):
        return _verdict(event, API_KEY_PRINCIPAL, API_KEY_PRINCIPAL, _the_workflows_operations)
    claims = _claims(token)
    email = str(claims.get('email', ''))
    return _verdict(event, email, _admission(claims, email), _every_operation)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    try:
        return _decided(event)
    except Unauthorized as refusal:
        _log(event, 'unknown', 'unauthorized', refusal.reason)
        raise
