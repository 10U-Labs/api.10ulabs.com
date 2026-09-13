import json
import logging
import os
import re
from typing import Any, Dict, Optional, Tuple
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from botocore.exceptions import ClientError

from lambda_http import aws_client, dispatch, json_response, parse_object

logger = logging.getLogger()
logger.setLevel(logging.INFO)

RECAPTCHA_URL = 'https://www.google.com/recaptcha/api/siteverify'
RECAPTCHA_MINIMUM_SCORE = 0.5
EMAIL_ADDRESS = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
LIMITS = {'name': 100, 'email': 255, 'message': 1000}
FIELDS = ('recaptcha_token', 'name', 'email', 'message')
CORS_HEADERS = {'Access-Control-Allow-Origin': '*'}
TEST_MODE_RESPONSE = {
    'success': True,
    'message': 'Test mode - contact form not submitted',
    'test_mode': True
}

def _error(status_code: int, message: str) -> Dict[str, Any]:
    return json_response(status_code, {'success': False, 'error': message})


def _fields(body: Dict[str, Any]) -> Dict[str, str]:
    return {name: str(body.get(name) or '').strip() for name in FIELDS}


def _validation_error(fields: Dict[str, str]) -> Optional[str]:
    for name in FIELDS:
        if not fields[name]:
            return f'Missing required field: {name}'
    for name, limit in LIMITS.items():
        if len(fields[name]) > limit:
            return f'{name.capitalize()} must be less than {limit} characters'
    if not EMAIL_ADDRESS.match(fields['email']):
        return 'Invalid email address'
    return None


def _is_test_mode(event: Dict[str, Any]) -> bool:
    headers = event.get('headers') or {}
    return any(key.lower() == 'x-test-mode' and value == 'true' for key, value in headers.items())


def _recaptcha_secret() -> str:
    parameter = aws_client('ssm').get_parameter(
        Name=os.environ['RECAPTCHA_SECRET_PARAMETER_NAME'], WithDecryption=True
    )
    return str(parameter['Parameter']['Value'])


def _recaptcha_passes(token: str, secret: str) -> bool:
    data = urlencode({'secret': secret, 'response': token}).encode('utf-8')
    try:
        with urlopen(Request(RECAPTCHA_URL, data=data, method='POST'), timeout=10) as response:
            verdict = json.loads(response.read().decode('utf-8'))
    except (URLError, OSError, ValueError) as error:
        logger.error('reCAPTCHA verification error: %s', error)
        return False
    return bool(verdict.get('success')) and verdict.get('score', 0) >= RECAPTCHA_MINIMUM_SCORE


def _send(fields: Dict[str, str]) -> None:
    recipient = os.environ['CONTACT_EMAIL']
    text = f"Name: {fields['name']}\nEmail: {fields['email']}\n\nMessage:\n{fields['message']}"
    aws_client('ses').send_email(
        Source=recipient,
        Destination={'ToAddresses': [recipient]},
        Message={
            'Subject': {'Data': f"Contact Form: Message from {fields['name']}", 'Charset': 'UTF-8'},
            'Body': {'Text': {'Data': text, 'Charset': 'UTF-8'}}
        },
        ReplyToAddresses=[fields['email']]
    )


def _accepted_fields(event: Dict[str, Any]) -> Tuple[Dict[str, str], Optional[str]]:
    body = parse_object(event)
    if body is None:
        return {}, 'Invalid JSON'
    fields = _fields(body)
    return fields, _validation_error(fields)


def _deliver(fields: Dict[str, str]) -> Dict[str, Any]:
    try:
        secret = _recaptcha_secret()
    except ClientError as error:
        logger.error('Failed to read the reCAPTCHA secret: %s', error)
        return _error(500, 'Server configuration error')
    if not _recaptcha_passes(fields['recaptcha_token'], secret):
        return _error(400, 'reCAPTCHA verification failed')
    try:
        _send(fields)
    except ClientError as error:
        logger.error('Failed to send the contact email: %s', error)
        return _error(500, 'Failed to send message')
    logger.info('Contact form submitted: name=%s, email=%s', fields['name'], fields['email'])
    return json_response(200, {'success': True, 'message': 'Message sent successfully'})


def _submit(event: Dict[str, Any]) -> Dict[str, Any]:
    fields, error = _accepted_fields(event)
    if error:
        return _error(400, error)
    if _is_test_mode(event):
        return json_response(200, TEST_MODE_RESPONSE)
    return _deliver(fields)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    response = dispatch(event, {('/contact-submissions', 'POST'): _submit})
    response['headers'].update(CORS_HEADERS)
    return response
