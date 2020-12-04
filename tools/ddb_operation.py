import boto3
from botocore.exceptions import ClientError
from boto_errors import ResponseStatusError, raise_for_status

# FIXME: use logger instead of `print()`

# -----------------------------------------------------------------------------
# DynamoDB Error Handling

CLIENT_ERROR_HELP_STRINGS = {
    # Operation specific errors
    'ConditionalCheckFailedException': 'Condition check specified in the operation failed, review and update the condition check before retrying', # noqa E501
    'TransactionConflictException': 'Operation was rejected because there is an ongoing transaction for the item, generally safe to retry with exponential back-off', # noqa E501
    'ItemCollectionSizeLimitExceededException': 'An item collection is too large, you\'re using Local Secondary Index and exceeded size limit of items per partition key.' + # noqa E501
                                                ' Consider using Global Secondary Index instead', # noqa E501
    # Common Errors
    'InternalServerError': 'Internal Server Error, generally safe to retry with exponential back-off', # noqa E501
    'ProvisionedThroughputExceededException': 'Request rate is too high. If you\'re using a custom retry strategy make sure to retry with exponential back-off.' + # noqa E501
                                              'Otherwise consider reducing frequency of requests or increasing provisioned capacity for your table or secondary index', # noqa E501
    'ResourceNotFoundException': 'One of the tables was not found, verify table exists before retrying', # noqa E501
    'ServiceUnavailable': 'Had trouble reaching DynamoDB. generally safe to retry with exponential back-off', # noqa E501
    'ThrottlingException': 'Request denied due to throttling, generally safe to retry with exponential back-off', # noqa E501
    'UnrecognizedClientException': 'The request signature is incorrect most likely due to an invalid AWS access key ID or secret key, fix before retrying', # noqa E501
    'ValidationException': 'The input fails to satisfy the constraints specified by DynamoDB, fix input before retrying', # noqa E501
    'RequestLimitExceeded': 'Throughput exceeds the current throughput limit for your account, increase account level throughput before retrying', # noqa E501
}


class UpdateItemError(Exception):
    """One or more DynamoDB `update_item` operations failed.

    Attributes
    ----------
    errors : [str]
        List of ids for which `update_item()` failed
    """

    def __init__(self, errors):
        self.errors = errors


def handle_client_error(error):
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']

    error_help_string = CLIENT_ERROR_HELP_STRINGS[error_code]

    print('[{error_code}] {help_string}. Error message: {error_message}'
          .format(error_code=error_code,
                  help_string=error_help_string,
                  error_message=error_message))


# -----------------------------------------------------------------------------
# Table-Based

def execute_query(table, input):
    """[summary]

    Parameters
    ----------
    table : boto3.dynamodb.Table
        DynamoDB table to update
    input : dict
        Args for `Table.query()`

        See: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Table.query

    Returns
    -------
    dict
        Response from AWS DynamoDB

    Raises
    ------
    botocore.exceptions.ClientError
        Request failed
    ResponseStatusError
        Scan was not successful
    BaseException
        Unknown error
    """  # noqa E501
    try:
        response = table.query(**input)
        raise_for_status(response)
        print("Query successful.")
        # return response.get('Items')
        return response
    except ClientError as error:
        handle_client_error(error)
        raise error
    except ResponseStatusError as error:
        print('[status_code] Error')
        raise error
    except BaseException as error:
        print("Unknown error while querying: "
              + error.response['Error']['Message'])
        raise error


def execute_scan(table, input):
    """[summary]

    Parameters
    ----------
    table : boto3.dynamodb.Table
        DynamoDB table to scan
    input : dict
        Args for `Table.scan()`

        See: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Table.scan

    Returns
    -------
    dict
        Response from AWS DynamoDB

    Raises
    ------
    botocore.exceptions.ClientError
        Request failed
    ResponseStatusError
        Scan was not successful
    BaseException
        Unknown error
    """  # noqa E501
    try:
        response = table.scan(**input)
        raise_for_status(response)
        print("Scan successful.")
        return response
    except ClientError as error:
        handle_client_error(error)
        raise error
    except ResponseStatusError as error:
        print('[status_code] Error')
        raise error
    except BaseException as error:
        print("Unknown error while scanning: "
              + error.response['Error']['Message'])
        raise error


def execute_update_item(table, input):
    """[summary]

    Parameters
    ----------
    table : boto3.dynamodb.Table
        DynamoDB table to update
    input : dict
        Args for `Table.update_item()`

        See: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#DynamoDB.Table.update_item

    Returns
    -------
    dict
        Response from AWS DynamoDB

    Raises
    ------
    botocore.exceptions.ClientError
        Request failed
    ResponseStatusError
        Scan was not successful
    BaseException
        Unknown error
    """  # noqa E501
    try:
        response = table.update_item(**input)
        raise_for_status(response)
        # print("Successfully updated item.")
        # return response.get('Items')
        return response
    except ClientError as error:
        handle_client_error(error)
        raise error
    except ResponseStatusError as error:
        print('[status_code] Error')
        raise error
    except BaseException as error:
        print("Unknown error while updating item: "
              + error.response['Error']['Message'])
        raise error


# -----------------------------------------------------------------------------
# Update Table

# TODO: add `raise_errors` (?) param to throw on first error so we don't waste
# our time on a bad update?
def update_items(
    table, items, update_input_builder, hash_key='id', verbose=False
):
    """Update `items` using input returned from `update_input_builder`

    Parameters
    ----------
    table : boto3.dynamodb.Table
        DynamoDB table to update
    items : list
        Items in `table` to update
    update_input_builder : (dict) -> dict
        Function returning input for `update_item()` from a DynamoDB item
    hash_key : str, optional
        DynamoDB HASH key for items
    verbose : bool, optional
        Description

    Returns
    -------
    dict
        updated_count : Int
            Number of items updated
        errors : list
            Item `hash_key`s that could not be updated
    """
    # TODO: use log rather than `print()
    updated_count = 0
    errors = []
    for item in items:
        try:
            update_input = update_input_builder(item)
            execute_update_item(table, update_input)
            updated_count += 1
            # if verbose:
            #     print(f"Successfully updated item '{item.get(hash_key)}'")
        except ClientError as e:
            # if raise_errors:
            #     raise e
            # else:
            errors.append(item.get(hash_key))
            # if verbose:
            print(f"Error updating item '{item.get(hash_key)}': {e}")
        except ResponseStatusError as e:
            # if raise_errors:
            #     raise e
            # else:
            errors.append(item.get(hash_key))
            # if verbose:
            print(f"Error updating item '{item.get(hash_key)}': {e}")
        except BaseException as e:
            # Handle any errors from `update_input_builder()`
            # if raise_errors:
            #     raise e
            # else:
            errors.append(item.get(hash_key)) 
            print(f"Error updating item '{item.get(hash_key)}': {e}")

    return {
        'updated_count': updated_count,
        'errors': errors
    }


def update_items_from_scan(
    table, scan_input, update_input_builder, hash_key='id', verbose=False
):
    """Perform scan on `table` using `scan_input` and update returned items
    using input returned from `update_input_builder`

    Parameters
    ----------
    table : boto3.dynamodb.Table
        DynamoDB table to update
    scan_input : dict
        Input for `scan()`
    update_input_builder : (dict) -> dict
        Function returning input for `update_item()` from a DynamoDB item
    hash_key : str, optional
        DynamoDB HASH key for items
    verbose : bool, optional
        Description

    Returns
    -------
    list
        List of item `hash_key`s that could not be updated

    Raises
    ------
    UpdateItemError
        Description
    """
    # TODO: use log rather than `print()`
    scan_count = 0
    last_key = True
    updated_count = 0
    errors = []
    while last_key is not None:
        print(f'Runnning scan: {scan_count}')

        if scan_count > 0:
            scan_input['ExclusiveStartKey'] = last_key

        items = []
        try:
            scan_resp = execute_scan(table, scan_input)
            items = scan_resp.get('Items', [])
            last_key = scan_resp.get('LastEvaluatedKey')
            scan_count += 1
        except ClientError as e:
            # TODO: how to handle?
            raise UpdateItemError(errors)
        except ResponseStatusError as e:
            # TODO: how to handle?
            raise UpdateItemError(errors)
        except BaseException as e:
            raise UpdateItemError(errors)
        
        if verbose:
            print(f'Updating {len(items)} items ...')
        
        # Update items
        r = update_items(table, items, update_input_builder, hash_key, verbose)
        updated_count += r['updated_count']
        errors += r['errors']

        if verbose:
            print(f"Updated {r['updated_count']} items with "
                  f"{len(r['errors'])} errors\n")

    # Finish
    if errors:
        print(f'Finished updating {updated_count} items; '
              f'unable to update: {errors}')
        # raise ddb.UpdateItemError(errors)
        return errors
    else:
        print(f'Finished updating {updated_count} items')


def update_items_from_query(
    table, query_input, update_input_builder, hash_key='id', verbose=False
):
    """Perform query on `table` using `query_input` and update returned items
    using input returned from `update_input_builder`

    Parameters
    ----------
    table : boto3.dynamodb.Table
        DynamoDB table to update
    scan_input : dict
        Input for `query()`
    update_input_builder : (dict) -> dict
        Function returning input for `update_item()` from a DynamoDB item
    hash_key : str, optional
        DynamoDB HASH key for items
    verbose : bool, optional
        Description

    Returns
    -------
    list
        List of item `hash_key`s that could not be updated

    Raises
    ------
    UpdateItemError
        Description
    """
    page_count = 0
    last_key = True
    updated_count = 0
    errors = []
    while last_key is not None:
        print(f'Runnning query: {page_count}')

        if page_count > 0:
            query_input['ExclusiveStartKey'] = last_key

        items = []
        try:
            scan_resp = execute_query(table, query_input)
            items = scan_resp.get('Items', [])
            last_key = scan_resp.get('LastEvaluatedKey')
            page_count += 1
        except ClientError as e:
            # TODO: how to handle?
            raise UpdateItemError(errors)
        except ResponseStatusError as e:
            # TODO: how to handle?
            raise UpdateItemError(errors)
        except BaseException as e:
            raise UpdateItemError(errors)

        if verbose:
            print(f'Updating {len(items)} items ...')

        # Update items
        r = update_items(table, items, update_input_builder, hash_key, verbose)
        updated_count += r['updated_count']
        errors += r['errors']

        if verbose:
            print(f"Updated {r['updated_count']} items with "
                  f"{len(r['errors'])} errors\n")

    # Finish
    if errors:
        print(f'Finished updating {updated_count} items; '
              f'unable to update: {errors}')
        # raise ddb.UpdateItemError(errors)
        return errors
    else:
        print(f'Finished updating {updated_count} items')


# -----------------------------------------------------------------------------
# Client-Based

def create_dynamodb_client(region="us-west-2"):
    if region == 'localhost':
        return boto3.client('dynamodb', region_name=region,
                            endpoint_url='http://localhost:8000',
                            aws_access_key_id='access_key_id',
                            aws_secret_access_key='secret_access_key')
    else:
        return boto3.client('dynamodb', region_name=region)
