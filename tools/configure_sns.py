#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Create and configure SNS Platform Applications for APNs notifications.
"""

import argparse
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import typing
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from config import Config
from boto_errors import ResponseStatusError
from boto_errors import raise_for_status


def get_amplify_setting(file_path: str, object_id: str) -> str:
    """Return value of key path `object_id` in JSON file at `file_path`

    Parameters
    ----------
    file_path : str
        Path of JSON file to read
    object_id : str
        Key path of value to return

    Returns
    -------
    str
        Value of `object_id`
    """
    # https://stackoverflow.com/a/4760517/4472195
    try:
        result = subprocess.run(
            ['jq', '-r', object_id, file_path],
            capture_output=True, text=True, check=True
        ).stdout.splitlines()
    except subprocess.CalledProcessError as e:
        logging.error(f'Error: {e.stderr}')
        # TODO: throw more generic error?
        raise e

    if not result:
        return
    result = result[0]
    if result == 'null':
        return
    return result


def get_apns_profile(path: os.PathLike, platform: str,
                     org_id: str) -> typing.Tuple[str, str]:
    """Return credential and principal for APNs profile `platform`

    Parameters
    ----------
    path : os.PathLike
        Path to directory containing `.pkey` and `.pem` files
    platform : str
        Type of APNs platform application
    org_id : str
        Organization identifier for client app

    Returns
    -------
    Tuple[str, str]
        Contents of APNs credential and principal

    Raises
    ------
    ValueError
        Invalid `platform`
    """
    if platform in ['prod', 'production']:
        f_name = f'production_{org_id}.Adequate'
    elif platform in ['dev', 'development']:
        f_name = f'development_{org_id}.Adequate'
    else:
        raise ValueError('Invalid platform')

    # Read certificates
    pkey = path / f'{f_name}.pkey'
    with open(pkey, 'r') as f1:
        credential = f1.read()

    pem = path / f'{f_name}.pem'
    with open(pem, 'r') as f2:
        principal = f2.read()

    return (credential, principal)


def create_platform_app_input(platform: str, pkey: str, pem: str) -> dict:
	"""Return input for `SNS.create_platform_application()` command

	Parameters
	----------
	platform : str
		Type of APNs platform application
	pkey : str
		Contents of `.pkey` file
	pem : str
		Contents of `.pem` file

	Returns
	-------
	dict
		Input for `SNS.create_platform_application()`

	Raises
	------
	ValueError
		Invalid `platform`
	"""
	if platform in ['prod', 'production']:
		name = Config.MASTER_SNS_APP_NAME
		platform = Config.MASTER_SNS_PLATFORM
	elif platform in ['dev', 'development']:
		name = Config.DEV_SNS_APP_NAME
		platform = Config.DEV_SNS_PLATFORM
	else:
		raise ValueError('Invalid platform')

	# TODO: IAM role for logging delivery status?
	return {
		'Name': name,
		'Platform': platform,
		'Attributes': {
			'PlatformCredential': pkey,
			'PlatformPrincipal': pem,
			# 'SuccessFeedbackRoleArn': # Write access for CloudWatch logs
			# 'FailureFeedbackRoleArn': # Write access for CloudWatch logs
		}
	}


def create_platform_application(sns_client, input: dict) -> str:
    """Create SNS Platform Applilcation and return corresponding ARN

    Parameters
    ----------
    sns_client : boto3.Client
        boto3 client for AWS SNS
    input : dict
        Input for `SNS.create_platform_application()`

    Returns
    -------
    str
        SNS Platform Application ARN

    Raises
    ------
    ClientError
        Request error
    ResponseStatusError
        Request was not successful
    BaseException
        Unknown error
    """
    try:
        response = sns_client.create_platform_application(input)
        raise_for_status(response)
    except ClientError as e:
        logging.error(f"Error with boto3 request: {e}")
        raise e
    except ResponseStatusError as e:
        logging.error('[status_code] Error')
        raise e
    except BaseException as e:
        logging.error("Unknown error while creating platform application: "
                      + e.response['Error']['Message'])
        raise e

    return response.get('PlatformApplicationArn')


def get_platform_application(client, platform: str, name: str,
                             next_token: Optional[str] = None) -> str:
    """Return ARN of AWS SNS platform application

    Parameters
    ----------
    client : boto3.Client
        boto3 client for AWS SNS
    platform : str
        AWS SNS platform
    name : str
        Name of AWS SNS platform application
    next_token : str, optional
        Token returned by AWS SNS when addition records are available, by
        default None

    Returns
    -------
    str
        ARN of AWS SNS platform application

    Raises
    ------
    ValueError
        Invalid `platform` value
    ResponseStatusError
        Request was not successful
    """
    if platform not in Config.VALID_SNS_PLATFORMS:
        raise ValueError('Invalid platfrom')

    kwargs = {}
    if next_token:
        kwargs['NextToken'] = next_token
    # try:
    resp = client.list_platform_applications(**kwargs)
    # except client.exceptions.InvalidParameterException as e:
    # except client.exceptions.InternalErrorException as e:
    # except client.exceptions.AuthorizationErrorException as e:

    platfrom_apps = resp.get('PlatformApplications')
    raise_for_status(resp)

    for app in resp.get('PlatformApplications'):
        arn = app.get('PlatformApplicationArn')
        arn_components = arn.split('/')
        if len(arn_components) < 3:
            continue
        if arn_components[-2] == platform:
            if arn_components[-1] == name:
                return arn

    token = resp.get('NextToken')
    if token:
        return get_platform_application(client, platform, name, token)


def get_topic_arn(client, stack_name: str,
                  next_token: Optional[str] = None) -> str:
    """Return ARN of AWS SNS topic used for APNs notifications in Adequate AWS
    SAM stack

    Parameters
    ----------
    client : boto3.Client
        boto3 client for CloudFormation
    stack_name : str
        Name of CloudFormation stack
    next_token : str, optional
        Token returned by AWS CloudFormation when additional stacks are
        available, by default None

    Returns
    -------
    str
        ARN of AWS SNS topic

    Raises
    ------
    ResponseStatusError
        Request was not successful
    botocore.exceptions.ClientError
        boto3 request failed
    """
    kwargs = {'StackName': stack_name}
    if next_token:
        kwargs['NextToken'] = next_token

    try:
        resp = client.describe_stacks(**kwargs)
    except ClientError as e:
        logging.error(f"Error with boto3 request: {e}")
        raise e
    # except client.exceptions.AmazonCloudFormationException as e:
    except BaseException as e:
        logging.error(f"Other error: {e}")
        raise e

    raise_for_status(resp)

    outputs = resp["Stacks"][0]["Outputs"]
    for output in outputs:
        keyName = output["OutputKey"]
        if keyName == "DealNotificationTopicOutput":
            return output["OutputValue"]

    token = resp.get('NextToken')
    if token:
        return get_topic_arn(client, stack_name, token)


def check_sns_policy_exists(client, role_name: str, policy_name: str,
                            next_token: Optional[str] = None) -> bool:
    """Check if inline policy `policy_name` already exists for IAM role
    `role_name`

    Parameters
    ----------
    client : boto3.Client
        boto3 client for IAM
    role_name : str
        Name of IAM role
    policy_name : [type]
        Name of inline policy on IAM role `role_name`
    next_token : str, optional
        Token returns by AWS IAM when additional policies are available, by
        default None

    Returns
    -------
    bool
        `True` if inline policy `policy_name` already exists on `role_name`,
        `False` if not

    Raises
    ------
    ResponseStatusError
        Request was not successful
    """
    kwargs = {'RoleName': role_name}
    if next_token:
        kwargs['Marker'] = next_token
    # try:
    resp = client.list_role_policies(**kwargs)
    # except client.exception.NoSuchEntityException as e:
    # except client.exceptions.ServiceFailureException as e:

    raise_for_status(resp)
    for policy in resp.get('PolicyNames', []):
        if policy == policy_name:
            return True

    token = resp.get('Marker')
    if token:
        return check_sns_policy_exists(client, role_name, policy_name, token)
    else:
        return False


def add_sns_policy(client, role_name: str, platform_application_arn: str,
                   topic_arn: str) -> dict:
    """Add inline policy to IAM role enabling access to an SNS platform
    application and SNS topic

    Parameters
    ----------
    client : boto3.Client
        boto3 client for SNS
    role_name : str
        Name of inline policy to add
    platform_application_arn : str
        ARN of SNS platform application
    topic_arn : str
        ARN of SNS topic

    Returns
    -------
    dict
        Response from SNS

    Raises
    ------
    ResponseStatusError
        Request was not successful
    """
    # Actions:  https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonsns.html
    policy_document = {
        'Version': '2012-10-17',
        'Statement': {
            'Effect': 'Allow',
            'Action': [
                'sns:ConfirmSubscription',
                'sns:CreatePlatformEndpoint',
                'sns:DeleteEndpoint',
                'sns:GetEndpointAttributes',  # ?
                'sns:Subscribe',  # ?
                'sns:Unsubscribe',
            ],
            'Resource': [
                platform_application_arn,
                topic_arn
            ]
        }
    }
    policy_document_string = json.dumps(policy_document)

    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html#IAM.Client.put_role_policy
    try:
        resp = client.put_role_policy(
            RoleName=role_name,
            PolicyName=Config.SNS_POLICY_NAME,
            PolicyDocument=policy_document_string
        )
    except ClientError as e:
        logging.error(f"Error with boto3 request: {e}")
        raise e
    # except client.exceptions.NoSuchEntityException as e:
    # except client.exceptions.UnmodifiableEntityException as e:
    # except client.exceptions.ServiceFailureException as e:
    # except client.exceptions.MalformedPolicyDocumentException as e:
    # except client.exceptions.LimitExceededException as e:
    except BaseException as e:
        logging.error(f"Other error: {e}")
        raise e

    raise_for_status(resp)
    return resp


def configure_for_branch(session, sam_base_name: str, env_name: str,
                         platform_application_arn: str):
    """Add inline policy to IAM unauth role for branch enabling access to APNs

    Enables access to both the SNS platform application and the SNS topic

    Parameters
    ----------
    session : boto3.Session
        AWS boto3 Session
    sam_base_name : str
        Base name for Adequate-Backend CloudFormation stacks
    env_name : str
        Name of Amplify environment and suffix for corresponding CloudFormation
        stack
    platform_application_arn : str
        ARN of SNS platform application

    Raises
    ------
    ResponseStatusError
        Request was not successful
    botocore.exceptions.ClientError
        boto3 request failed
    """
    # Get name of unauth role for amplify environment
    role_name_id = f'.{env_name}.awscloudformation.UnauthRoleName'
    role_name = get_amplify_setting(Config.TEAM_PROVIDER_INFO, role_name_id)

    # Get ARN of SNS topic for corresponding CloudFormation stack
    topic_arn = get_topic_arn(session.client('cloudformation'),
                              f'{sam_base_name}-{env_name}')

    iam = session.client('iam')

    # Verify inline policy does not already exist
    policy_exists = check_sns_policy_exists(iam, role_name,
                                            Config.SNS_POLICY_NAME)
    if policy_exists:
        logging.info(
            f"Inline policy '{Config.SNS_POLICY_NAME}' already exists for IAM "
            f"role '{role_name}'"
        )
        return

    # Add inline policy to unauth role
    try:
        resp = add_sns_policy(iam, role_name, platform_application_arn,
                              topic_arn)
    except ClientError as e:
        logging.error(f"Error with boto3 request: {e}")
        raise e
    raise_for_status(resp)
    return resp


# -----------------------------------------------------------------------------
# CLI

def reverse_dns(value: str) -> str:
    """Validate `--org` argument

    Parameters
    ----------
    value : str
        Passed by the ArgumentParser object

    Returns
    -------
    str
        Returns the value back to the ArgumentParser object

    Raises
    ------
    argparse.ArgumentTypeError
        The passed argument was not in reverse DNS notation
    """
    # https://en.wikipedia-on-ipfs.org/wiki/Reverse_domain_name_notation.html
    regex = '^[A-Za-z]{2,6}((?!-)\.[A-Za-z0-9-]{1,63}(?<!-))+$'
    p = re.compile(regex)
    if not re.match(p, value):
        raise argparse.ArgumentTypeError(
            f"'{value}' not in reverse DNS notation")
    return value


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTIONS] [TABLE]",
        description="Create and configure SNS Platform Applications for APNs."
    )
    parser.add_argument(
        "-v", "--version", action="version",
        version=f"{parser.prog} version 1.0.0"
    )

    parser.add_argument('--base-name', metavar='stack-name',
                        default=Config.DEFAULT_BASE_STACK_NAME,
                        help='Base name for AWS CloudFormation stacks')

    parser.add_argument('--region', default=None,
                        help='AWS region name for resources')

    parser.add_argument('--org', default='com.mgacy',
                        help='Organization identifier for iOS client app',
                        type=reverse_dns)

    parser.add_argument('--server', default='both',
                        help='APNs server to use',
                        choices=['dev', 'prod', 'both'])

    parser.add_argument('--verbose', action='store_true',
                        help='Increase output verbosity')

    # TODO: implement
    # parser.add_argument('--client', default=None,
    #                     help='Path to root client directory')

    return parser


def main():
    parser = init_argparse()
    args = parser.parse_args()

    # if args.path:
    #     path = Path(args.path)
    # else:
    path = Path(__file__).parent / "../../Adequate"

    if args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(level=log_level,
                        format=Config.LOG_FORMAT)

    kwargs = {}
    if args.region:
        kwargs['region_name'] = args.region
    session = boto3.Session(**kwargs)
    sns = session.client('sns')

    # Branch: dev
    if args.server in ['dev', 'both']:
        logging.info(
            f"Configuring unauth role for '{Config.DEV_BRANCH_SUFFIX}' "
            "environment...")
        (pkey, pem) = get_apns_profile(path, 'dev', args.org)
        dev_input = create_platform_app_input('dev', pkey, pem)
        apns_sandbox = create_platform_application(sns, dev_input)

        # try:
        dev_resp = configure_for_branch(session, args.base_name,
                                        Config.DEV_BRANCH_SUFFIX,
                                        apns_sandbox)
        # except BaseException as e:

    # Branch: master
    if args.server in ['prod', 'both']:
        logging.info(
            f"Configuring unauth role for '{Config.MASTER_BRANCH_SUFFIX}'"
            "environment...")
        (pkey, pem) = get_apns_profile(path, 'prod', args.org)
        prod_input = create_platform_app_input('prod', pkey, pem)
        apns = create_platform_application(sns, prod_input)

        # try:
        prod_resp = configure_for_branch(session, args.base_name,
                                        Config.MASTER_BRANCH_SUFFIX, apns)
        # except BaseException as e:


if __name__ == '__main__':
    main()
