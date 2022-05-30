"""
"""
import json
import os
from datetime import datetime, timedelta
import jwt
from decouple import config

def jwt_token():
    """
    Generate a JWT token for the Google Earth Engine API.
    Reference: https://developers.google.com/identity/protocols/oauth2#serviceaccount
    """

    # https://developers.google.com/identity/protocols/oauth2/service-account
    # https://developers.google.com/earth-engine/reference/rest?hl=en_GB
    # https://developers.google.com/identity/protocols/oauth2/service-account#python_2

    # we take our service account details as provided by the google console:
    service_account_config = config('service_account_config')
    if os.path.exists(service_account_config):
        with open(service_account_config) as f:
            service_account = json.load(f)
    else:
        service_account = {
            'client_email': config('client_email'),
            'private_key': config('private_key').replace('\\n', '\n'),
            'private_key_id': config('private_key_id')
        }

    iat = datetime.now()
    exp = iat + timedelta(seconds=3600)

    payload = {
        'iss': service_account['client_email'],
        'sub': service_account['client_email'],
        'aud': 'https://earthengine.googleapis.com/',
        'iat': int(iat.timestamp()),
        'exp': int(exp.timestamp())
    }

    additional_headers = {
        'kid': service_account['private_key_id']
    }

    # sign the payload using the private key
    token = jwt.encode(
        payload,
        service_account['private_key'],
        headers=additional_headers,
        algorithm='RS256')

    return token