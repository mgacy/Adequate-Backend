"""
Create KMS Customer Master Key and `env-vars.sh`
"""

import logging
import os
from pathlib import Path
import typing
import boto3
from botocore.exceptions import ClientError
from config import Config
from boto_errors import ResponseStatusError
from boto_errors import raise_for_status

ENV_VARS_PATH = '.env'

ENV_TEMPLATE = """export AWS_REGION={aws_region}
export BASE_NAME=adequate-sam
export KMS_KEY_ID={kms_key_id}
export APNS_CATEGORY=MGDailyDealCategory
export PLAIN_API_KEY=
# export ALARM_EMAIL=
"""


def create_cmk(client, desc='Customer Master Key') -> str:
    """Create a KMS Customer Master Key

    The created CMK is a Customer-managed key stored in AWS KMS.

    Parameters
    ----------
    client : boto3.Client
        boto3 client for AWS KMS
    desc : str, optional
        Key description, by default 'Customer Master Key'

    Returns
    -------
    str
        AWS globally-unique string ID

    Raises
    ------
    ClientError
        Request error
    ResponseStatusError
        Request was not successful
    """
    try:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/kms.html#KMS.Client.create_key
        response = client.create_key(Description=desc)
        raise_for_status(response)
    except ClientError as e:
        logging.error(e)
        raise e
    except ResponseStatusError as e:
        logging.error('[status_code] Error')
        raise e

    return response['KeyMetadata']['KeyId']


def create_alias(client, key_id: str, alias: str):
    """Add alias for KMS Customer Master Key.

    Parameters
    ----------
    client : boto3.Client
        boto3 client for AWS KMS
    key_id : str
        KMS key id
    alias : str
        Alias to apply to KMS key

    Raises
    ------
    ClientError
        Request error
    ResponseStatusError
        Request was not successful
    """
    try:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/kms.html#KMS.Client.create_alias
        response = client.create_alias(
            AliasName=f'alias/{alias}',
            TargetKeyId=key_id
        )
        raise_for_status(response)
    except ClientError as e:
        logging.error(e)
        raise e
    except ResponseStatusError as e:
        logging.error('[status_code] Error')
        raise e


def create_env_file(f_path: os.PathLike, aws_region: str, kms_key_id: str):
    """Create shell script to set environment variables used during deployment

    Parameters
    ----------
    f_path : os.PathLike
        [description]
    aws_region : str
        AWS region
    kms_key_id : str
        KMS key id
    """
    contents = ENV_TEMPLATE.format(
        aws_region=aws_region,
        kms_key_id=kms_key_id
    )
    with open(f_path, 'x') as f:
        f.write(contents)


# -----------------------------------------------------------------------------

def main():

    logging.basicConfig(level=logging.INFO,
                        format=Config.LOG_FORMAT)

    kms_client = boto3.client('kms')

    key_id = create_cmk(kms_client, Config.KMS_DESCRIPTION)
    try:
        create_alias(kms_client, key_id, Config.KMS_ALIAS)
    except BaseException as e:
        logging.error(f"Unable to create alias for KMS key '{key_id}'")

    path = Path(__file__).parent / f'../{ENV_VARS_PATH}'
    # TODO: get region from Amplify config
    aws_region = kms_client.meta.region_name
    create_env_file(path, aws_region, key_id)


if __name__ == '__main__':
    main()
