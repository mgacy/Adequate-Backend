import datetime as dt
import decimal
import json
import logging
import os
import boto3
from boto3 import resource
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from tz_support import Eastern

# Configure logging
# https://docs.aws.amazon.com/lambda/latest/dg/python-logging.html
# https://stackoverflow.com/a/56579088/4472195
logger = logging.getLogger()
if logging.getLogger().hasHandlers():
    # The Lambda environment pre-configures a handler logging to stderr.
    # To customize format, see: https://stackoverflow.com/a/45624044/4472195
    logging.getLogger().setLevel(logging.INFO)
else:
    logging.basicConfig(level=logging.INFO)

logger.info('Loading function')

DEAL_TABLE_NAME = os.environ['DEAL_TABLE_NAME']
# TODO: should these be environment variables?
INDEX_NAME = 'isRecent-createdAt-index'
PERIOD_LENGTH = 30

dynamodb = resource('dynamodb')
table = dynamodb.Table(DEAL_TABLE_NAME)


# -----------------------------------------------------------------------------
# Support

class ResponseStatusError(Exception):
    """A boto3 request was not successful.

    Attributes
    ----------
    msg : str
        Error message
    response : dict
        Request response
    """

    def __init__(self, status_code, response):
        # TODO: map different errors (400 - 499 / 500 - 599)?
        self.msg = f'Error: {status_code}'
        # TODO: extract `response['ResponseMetadata']`?
        self.response = response


class UpdateItemError(Exception):
    """One or more DynamoDB `update_item` operations failed.

    Attributes
    ----------
    errors : [str]
        List of ids for which `update_item()` failed
    """

    def __init__(self, errors):
        self.errors = errors


# -----------------------------------------------------------------------------
# Functions

def raise_for_status(response):
    """Raises `ResponseStatusError` if boto3 request was not successful.

    Parameters
    ----------
    response : dict
        Response from boto3 request

    Raises
    ------
    ResponseStatusError
        Response status code was not 200
    """
    status_code = response.get('ResponseMetadata', {}).get('HTTPStatusCode')
    if status_code != 200:
        logger.error(response)
        raise ResponseStatusError(status_code, response)


def ingest_event(event):
    """Return `dict` mapping table name to HASH key for `INSERT` events in DynamoDB

    Parameters
    ----------
    event: dict
        DynamoDB stream event

        DynamoDB events doc: https://docs.aws.amazon.com/lambda/latest/dg/with-ddb.html

    Returns
    -------
    dict {str : str}
        Maps table name to record HASH key
    """  # noqa E501
    insertions = {}
    for record in event['Records']:
        if record['eventName'] != 'INSERT':
            continue

        id = record['dynamodb']['Keys'].get('id', {}).get('S', None)
        if id is None:
            logger.error(f"Failed to get id for Record: {json.dumps(record)}")
            continue

        source = record['eventSourceARN']
        try:
            table_name = source.split(':table/')[1].split('/')[0]
            insertions[id] = table_name
        except IndexError:
            logger.error(f"Failed to get table name from '{source}'")
            continue

        # FIXME: we would want errors to make their way (somewhere)

    return insertions


def add_recent(table, id):
    """Add `isRecent` attribute to DynamoDB record in `table` with HASH `id`

    Parameters
    ----------
    table : boto3.DynamoDB.Table
        DynamoDB table
    id : str
        DynamoDB record HASH Key

    Returns
    -------
    dict
        [description]

    Raises
    ------
    AppError
        Update failed
    ClientError
        Request to DynamoDB failed
    """
    response = table.update_item(
        Key={'id': id},
        UpdateExpression='SET isRecent=:r',
        ExpressionAttributeValues={
            ':r': decimal.Decimal(1)
        },
        ReturnValues='UPDATED_NEW'
    )
    raise_for_status(response)
    return response


def query_outdated_history(table, index_name, cutoff_date):
    """Return deal records created before `cutoff_date` with `isRecent` attr

    Parameters
    ----------
    table : boto3.DynamoDB.Table
        DynamoDB table to query
    index_name : str
        Name of DynamoDB GSI to query
    cutoff_date : datetime
        Will query for records with `createdAt` before `cutoff_date`

    Returns
    -------
    dict
        [description]

    Raises
    ------
    AppError
        Query failed
    ClientError
        Request to DynamoDB failed
    """
    response = table.query(
        IndexName=index_name,
        Select='ALL_PROJECTED_ATTRIBUTES',
        KeyConditionExpression=(
            Key('isRecent').eq(1)
            & Key('createdAt').lt(
                format_date(cutoff_date)
            )
        )
        # FilterExpression=filter
    )
    raise_for_status(response)
    return response.get('Items')


def format_date(date):
    """Return ISO 8601 date string for `date`

    Uses format `YYYY-MM-DDThh:mm:ss.sTZD`

    Parameters
    ----------
    date : datetime
        Date to format

    Returns
    -------
    str
        ISO 8601 formatted date string
    """
    return (date.strftime('%Y-%m-%dT%H:%M:%S')
            + date.strftime('.%f')[:4] + 'Z')


def remove_recent(table, id):
    """Remove `isRecent` attribute from DynamoDB record with HASH key `id`

    Parameters
    ----------
    table : boto3.DynamoDB.Table
        DynamoDB table to update
    id : str
        HASH Key of record to update

    Returns
    -------
    dict
        [description]

    Raises
    ------
    AppError
        Update failed
    ClientError
        Request to DynamoDB failed
    """
    response = table.update_item(
        Key={'id': id},
        UpdateExpression='REMOVE isRecent',
        ReturnValues='UPDATED_NEW'
    )
    raise_for_status(response)
    return response


def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': str(err) if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        }
    }


# -----------------------------------------------------------------------------
# Lambda Handler

def handler(event, context):
    """AWS Lambda Function entrypoint to fetch deal from meh.com and update
    AppSync GraphQL API.

    Parameters
    ----------
    event: dict, required
        DynamoDB stream event

        DynamoDB events doc: https://docs.aws.amazon.com/lambda/latest/dg/with-ddb.html

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    dict
        DESCRIPTION
    """  # noqa E501
    global table

    logger.info(f'Received event: {json.dumps(event, indent=2)}')

    insertion_records = ingest_event(event)
    if not insertion_records:
        return respond(None, 'No INSERTIONs to process.')

    # Add newly created records to history
    insertions = []
    insertion_errors = []
    for id, event_table in insertion_records.items():
        if event_table != table.name:
            logger.error(f"Unexpected table for id '{id}': '{event_table}'")
            insertion_errors.append(id)
            continue

        try:
            r = add_recent(table, id)
            insertions.append(id)
        except ClientError as e:
            logger.error(e)
            insertion_errors.append(id)
        except ResponseStatusError as e:
            logger.error(e)
            insertion_errors.append(id)

    logger.info(f'Deals added to history: {insertions}')

    # Remove outdated deals from history
    cutoff_date = dt.datetime.now(tz=Eastern) - dt.timedelta(days=PERIOD_LENGTH)
    try:
        outdated = query_outdated_history(table, INDEX_NAME, cutoff_date)
    except ClientError as e:
        # TODO: simply retry?
        return respond(e)
    except ResponseStatusError as e:
        return respond(e)

    removals = []
    removal_errors = []
    for deal_id in [d['id'] for d in outdated]:
        try:
            r = remove_recent(table, deal_id)
            removals.append(deal_id)
        except ClientError as e:
            # TODO: simply retry?
            removal_errors.append(deal_id)
        except ResponseStatusError as e:
            removal_errors.append(deal_id)

    logger.info(f'Deals removed from history: {removals}')

    # Handle errors
    errors = insertion_errors + removal_errors
    if errors:
        if insertion_errors:
            logger.error(f'Failed to insert: {insertion_errors}')
        if removal_errors:
            logger.error(f'Failed to remove: {removal_errors}')
        return respond(UpdateItemError(errors))

    # TODO: form JSON message?
    message = f"Updated History - INSERTED: {insertions} - REMOVED: {removals}"
    return respond(None, message)
