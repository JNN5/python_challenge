import json
from typing import Union
import boto3
import base64
import logging
from botocore.exceptions import ClientError

log = logging.getLogger()
if log.handlers:
    HANDLER = log.handlers[0]
else:
    HANDLER = logging.StreamHandler()
    log.addHandler(HANDLER)
log_format = '[%(levelname)s] %(asctime)s- %(message)s (File %(pathname)s, Line %(lineno)s)'
HANDLER.setFormatter(logging.Formatter(log_format))
log.setLevel(logging.INFO)


def get_secret(secret_arn: str) -> Union[dict, bytes]:
    # Create a Secrets Manager client
    secrets_client = boto3.client('secretsmanager')
    # Code taken from AWS
    try:
        get_secret_value_response = secrets_client.get_secret_value(
            SecretId = secret_arn
        )
    except ClientError as e:
        log.info(e)
    else:
        # Decrypts secret using the associated KMS key.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            secret = json.loads(secret)
            return secret
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            return decoded_binary_secret

    return {}