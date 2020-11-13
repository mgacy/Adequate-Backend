#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# 11/11/20

import argparse
import json
# import logging
import os
import subprocess
import sys
import boto3
from botocore.exceptions import ClientError
from boto_errors import ResponseStatusError
from boto_errors import raise_for_status


# Default base name for AWS CloudFormation stacks
DEFAULT_BASE_STACK_NAME = 'adequate-sam'

# Relative path of amplify configuration file
TEAM_PROVIDER_INFO = '../amplify/team-provider-info.json'

# Relative path of amplify environment configuration file
# AMPLIFY_META = '../amplify/#current-cloud-backend/amplify-meta.json'

# Name of Amplify development environment and suffix for corresponding
# CloudFormation stack
DEV_BRANCH_SUFFIX = 'dev'

# AWS SNS platform for APNs sandbox
DEV_SNS_PLATFORM = 'APNS_SANDBOX'

# Name of AWS SNS platform application using APNs sandbox
DEV_SNS_APP_NAME = 'Adequate-Development'

# Name of Amplify production environment and suffix for corresponding
# CloudFormation stack
MASTER_BRANCH_SUFFIX = 'master'

# AWS SNS platform for APNs
MASTER_SNS_PLATFORM = 'APNS'

# Name of AWS SNS platform application using APNs
MASTER_SNS_APP_NAME = 'Adequate-Production'

# Name of inline policy to attach to unauth IAM role
POLICY_NAME = 'APNs_SNSAccess'

# Valid AWS SNS platforms
VALID_PLATFORMS = [DEV_SNS_PLATFORM, MASTER_SNS_PLATFORM]


# Configure logging
# logger = logging.getLogger()
# logging.basicConfig(level=logging.INFO


# -----------------------------------------------------------------------------

def get_amplify_setting(file_path, object_id):
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
        print(f'Error: {e.stderr}')
        # TODO: throw more generic error?
        raise e

    if not result:
        return
    result = result[0]
    if result == 'null':
        return
    return result


def get_platform_application(client, platform, name, next_token=None):
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
    if platform not in VALID_PLATFORMS:
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


def get_topic_arn(client, stack_name, next_token=None):
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
        print(f"Error with boto3 request: {e}")
        raise e
    # except client.exceptions.AmazonCloudFormationException as e:
    except BaseException as e:
        print(f"Other error: {e}")
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


def check_sns_policy_exists(client, role_name, policy_name, next_token=None):
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


def add_sns_policy(client, role_name, platform_application_arn, topic_arn):
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
            PolicyName=POLICY_NAME,
            PolicyDocument=policy_document_string
        )
    except ClientError as e:
        print(f"Error with boto3 request: {e}")
        raise e
    # except client.exceptions.NoSuchEntityException as e:
    # except client.exceptions.UnmodifiableEntityException as e:
    # except client.exceptions.ServiceFailureException as e:
    # except client.exceptions.MalformedPolicyDocumentException as e:
    # except client.exceptions.LimitExceededException as e:
    except BaseException as e:
        print(f"Other error: {e}")
        raise e

    raise_for_status(resp)
    return resp


def configure_for_branch(session, sam_base_name, env_name,
                         platform_application_arn):
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
    role_name = get_amplify_setting(TEAM_PROVIDER_INFO, role_name_id)
    # print(f'Unauth Role Name: {role_name}')

    # Get ARN of SNS topic for corresponding CloudFormation stack
    topic_arn = get_topic_arn(session.client('cloudformation'),
                              f'{sam_base_name}-{env_name}')
    # print(f'Topic ARN: {topic_arn}')

    iam = session.client('iam')

    # Verify inline policy does not already exist
    policy_exists = check_sns_policy_exists(iam, role_name, POLICY_NAME)
    if policy_exists:
        print(
            f"Inline policy '{POLICY_NAME}' already exists for IAM role "
            f"'{role_name}'"
        )
        return

    # Add inline policy to unauth role
    try:
        resp = add_sns_policy(iam, role_name, platform_application_arn,
                              topic_arn)
    except ClientError as e:
        print(f"Error with boto3 request: {e}")
        raise e
    raise_for_status(resp)
    return resp


# -----------------------------------------------------------------------------
# CLI

def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTIONS] [TABLE]",
        description="Configure GSI for Query.dealQuery."
    )
    parser.add_argument(
        "-v", "--version", action="version",
        version=f"{parser.prog} version 1.0.0"
    )

    parser.add_argument('--base-name', metavar='stack-name',
                        default=DEFAULT_BASE_STACK_NAME,
                        help='Base name for AWS CloudFormation stacks')

    parser.add_argument('--region', default=None,
                        help='AWS region name for resources')

    return parser


def main():
    parser = init_argparse()
    args = parser.parse_args()
    kwargs = {}
    if args.region:
        kwargs['region_name'] = args.region

    session = boto3.Session(**kwargs)
    sns = session.client('sns')

    # Branch: dev
    print(f"Configuring unauth role for '{DEV_BRANCH_SUFFIX}' environment...")
    apns_sandbox = get_platform_application(
        sns, DEV_SNS_PLATFORM, DEV_SNS_APP_NAME)

    # try:
    dev_resp = configure_for_branch(session, args.base_name, DEV_BRANCH_SUFFIX,
                                    apns_sandbox)
    # except BaseException as e:

    # Branch: master
    print(f"Configuring unauth role for '{MASTER_BRANCH_SUFFIX}' environment...")
    apns = get_platform_application(
        sns, MASTER_SNS_PLATFORM, MASTER_SNS_APP_NAME)

    # try:
    prod_resp = configure_for_branch(session, args.base_name,
                                     MASTER_BRANCH_SUFFIX, apns)
    # except BaseException as e:


if __name__ == '__main__':
    main()
