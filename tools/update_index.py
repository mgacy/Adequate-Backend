"""
Update sparse index for AppSync Query.dealHistory
"""
import argparse
import datetime as dt
import decimal
import json
# import logging
import os
from boto3 import resource
from boto3.dynamodb.conditions import Attr
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from boto_errors import ResponseStatusError
from boto_errors import raise_for_status
from ddb_operation import UpdateItemError
from ddb_operation import execute_query
from ddb_operation import update_items
from tz_support import Eastern

DATE_INDEX_NAME = 'byYearMonthDate'

# Configure logging
# logger = logging.getLogger()
# logging.basicConfig(level=logging.INFO)


# -----------------------------------------------------------------------------
# Builders

def create_deal_history_query_input(index_name, start_date, end_date):
    """Return input for DynamoDB query for deals created between `start_date`
    and `end_date` that are not `isRecent`.

    Parameters
    ----------
    index_name : str
        Name of DynamoDB GSI to query
    start_date : datetime
        Beginning to date range to query
    end_date : datetime
        End of date range to query

    Returns
    -------
    dict
        Input for DynamoDB query
    """
    return {
        'IndexName': index_name,
        # 'Select': 'ALL_ATTRIBUTES',
        'Select': 'ALL_PROJECTED_ATTRIBUTES',
        'KeyConditionExpression': (
            Key('dealYear').eq(end_date.strftime('%Y'))
            & Key('monthDay').between(start_date.strftime('%m%d'),
                                      end_date.strftime('%m%d'))
        ),
        'FilterExpression': (
            Attr('isRecent').ne(1) & Attr('id').ne('current_deal')
        )
    }


def create_update_item_input(item):
    """Return input for DynamoDB `update_item()` operation on `item` setting
    `isRecent` to `1`.

    Parameters
    ----------
    item : dict
        DynamoDB `Deal` item to update

    Returns
    -------
    dict
        Input for DynamoDB `update_item` operation
    """
    return {
        'Key': {'id': item['id']},
        'UpdateExpression': 'SET isRecent=:r',
        'ExpressionAttributeValues': {
            ':r': decimal.Decimal(1)
        },
        'ReturnValues': 'UPDATED_NEW'
    }


# -----------------------------------------------------------------------------
# Functions

# TODO: use more descriptive name; add optional `end_date` param
def get_deal_history(table, index_name, period_length=30):
    """Return results from query on a DynamoDB GSI.

    Parameters
    ----------
    table : boto3.dynamodb.Table
        DynamoDB table to query
    index_name : str
        Name of DynamoDB GSI to query
    period_length : int, optional
        Timespan to query. Must be between 0 and 365, by default 30

    Returns
    -------
    dict
        Response from query

    Raises
    ------
    ValueError
        Invalid `period_length`
    ResponseStatusError
        Query was not successful
    """
    end_date = dt.datetime.now(tz=Eastern)
    start_date = end_date - dt.timedelta(days=period_length)

    # Build query
    query_input = []
    if end_date.year == start_date.year:
        query_input.append(create_deal_history_query_input(
            index_name, start_date, end_date))

    elif end_date.year - start_date.year == 1:
        end_date_1 = start_date.replace(month=12, day=31)
        query_input.append(create_deal_history_query_input(
            index_name, start_date, end_date_1))

        start_date_2 = end_date.replace(month=1, day=1)
        query_input.append(create_deal_history_query_input(
            index_name, start_date_2, end_date))

    else:
        raise ValueError(
            "'period_length' must be a positive integer less than 365")

    # Execute query
    items = []
    for qi in query_input:
        try:
            resp = execute_query(table, qi)
            raise_for_status(resp)
            items += resp['Items']
        except ClientError as e:
            raise e
        except ResponseStatusError as e:
            raise e
        except BaseException as e:
            raise e

    return items


# -----------------------------------------------------------------------------
# CLI

def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTIONS] [TABLE]",
        description="Update dealHistory."
    )
    parser.add_argument(
        "-v", "--version", action="version",
        version=f"{parser.prog} version 1.0.0"
    )
    parser.add_argument('table_name', metavar='table-name')
    parser.add_argument('--index', metavar='index-name',
                        default=DATE_INDEX_NAME)
    return parser


def main():
    parser = init_argparse()
    args = parser.parse_args()

    dynamodb = resource('dynamodb')
    table = dynamodb.Table(args.table_name)

    deals = get_deal_history(table, args.index)
    deal_dates = [d['createdAt'] for d in deals]

    # print(f'Updating deals for {deal_dates} ...')
    print(f'Updating {len(deal_dates)} deals ...')
    r = update_items(table, deals, create_update_item_input, 'id', True)
    updated_count = r['updated_count']
    errors = r['errors']

    # TODO: create record of failed updates?
    if errors:
        print(f'Finished updating {updated_count} items; unable to update: {errors}')
    else:
        print(f'Finished updating {updated_count} items')


if __name__ == '__main__':
    main()
