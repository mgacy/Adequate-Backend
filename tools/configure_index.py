import argparse
# import logging
import os
import sys
import boto3
from botocore.exceptions import ClientError
from ddb_operation import ResponseStatusError
from ddb_operation import raise_for_status

RECENT_INDEX_NAME = 'isRecent-createdAt-index'
# TODO: use different values for master / develop?
DEFAULT_READ_UNITS = 3  # 5?
DEFAULT_WRITE_UNITS = 1  # 2?

# Configure logging
# logger = logging.getLogger()
# logging.basicConfig(level=logging.INFO

# BILLING_MODES = [
#     'PROVISIONED',
#     'PAY_PER_REQUEST'
# ]


# -----------------------------------------------------------------------------

def check_gsi_exists(client, table_name, index_name):
    """Check if GSI `index_name` already exists for DynamoDB table `table_name`

    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Client.describe_table

    Parameters
    ----------
    client : boto3.Client
        boto3 Client
    table_name : str
        DynamoDB table name
    index_name : str
        DynamoDB GSI name

    Returns
    -------
    bool
        `True` if `index_name` already exists, `False` if not

    Raises
    ------
    ResponseStatusError
        Request was not successful
    botocore.exceptions.ClientError
        boto3 request failed
    """
    try:
        resp = client.describe_table(TableName=table_name)
        raise_for_status(resp)
    except ClientError as e:
        print(f"Error with boto3 request: {e}")
        raise e
    except ResponseStatusError as e:
        print(f"Error describing table '{table_name}': {resp}")
        raise e

    table = resp['Table']
    indexes = [i.get('IndexName', None) for i in table.get(
        'GlobalSecondaryIndexes', [])]

    return index_name in indexes


# https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Client.update_table
def create_gsi(client, table_name, index_name,
               read_units=None, write_units=None):
    """Create new GSI for DynamoDB table

    Parameters
    ----------
    client : boto3.Client
        boto3 Client
    table_name : str
        Name of DynamoDB table
    index_name : str
        Name for GSI
    read_units : int, optional
        DynamoDB ReadCapacityUnits for index if table is Provisioned, by default None
    write_units : int, optional
         DynamoDB WriteCapacityUnits for index if table is Provisioned, by default None

    Returns
    -------
    dict
        [description]
    """  # noqa E501
    gsi_config = {
        'Create': {
            'IndexName': index_name,
            'KeySchema': [
                {
                    'AttributeName': 'isRecent',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'createdAt',
                    'KeyType': 'RANGE'
                }
            ],
            'Projection': {
                'ProjectionType': 'ALL'
            }
        }
    }

    # Only valid if table's read/write capacity mode is Provisioned
    if read_units and write_units:
        gsi_config['Create']['ProvisionedThroughput'] = {
            'ReadCapacityUnits': read_units,
            'WriteCapacityUnits': write_units
        }

    resp = client.update_table(
        AttributeDefinitions=[
            {
                'AttributeName': 'isRecent',
                'AttributeType': 'N'
            },
            {
                'AttributeName': 'createdAt',
                'AttributeType': 'S'
            }
        ],
        TableName=table_name,
        GlobalSecondaryIndexUpdates=[gsi_config]
    )
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
    parser.add_argument('table_name', metavar='table-name')
    parser.add_argument('--index', metavar='index-name',
                        default=RECENT_INDEX_NAME,
                        help='Override default name for GSI')
    # TODO: add support for `PAY_PER_REQUEST` `BillingMode`
    # parser.add_argument('--billing-mode', choices=BILLING_MODES, default='PROVISIONED')
    parser.add_argument('--read', type=int, default=DEFAULT_READ_UNITS,
                        help='ReadCapacityUnits for GSI')
    parser.add_argument('--write', type=int, default=DEFAULT_WRITE_UNITS,
                        help='WriteCapacityUnits for GSI')
    return parser


def main():
    parser = init_argparse()
    args = parser.parse_args()

    client = boto3.client('dynamodb')

    if check_gsi_exists(client, args.table_name, args.index):
        print(f"Table '{args.table_name}' already contains GSI '{args.index}'")
        return

    # Create GSI
    # index_response = create_gsi(client, args.table_name, args.index,)
    index_response = create_gsi(client, args.table_name, args.index,
                                args.read, args.write)
    print(index_response)
    raise_for_status(index_response)


if __name__ == '__main__':
    main()
