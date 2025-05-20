"""
Fonctions d'authentification et gestion des clés API.
"""

import json
import boto3
from botocore.exceptions import ClientError

from utils.config import TECH_CONFIG



_keycache = None 
def _get_keys():
    """
    Retrieves the OpenAI API key from AWS Secrets Manager.
    Assumes the secret is a JSON with a field named 'API_KEY'.
    """
    global _keycache 
    if _keycache is None :
        secret_name = TECH_CONFIG['secret_name']
        region_name = TECH_CONFIG['aws_region']

        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )

        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name
            )
        except ClientError as e:
            # For a list of exceptions thrown, see
            # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
            raise e

        secret = get_secret_value_response['SecretString']
        _keycache = json.loads(secret)
    return _keycache