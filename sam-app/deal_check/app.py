from base64 import b64decode
from datetime import datetime as dt
import json
import logging
import os
import boto3
from requests.exceptions import RequestException
import adequate
from appsync import AppSync, AppSyncException

API_ENDPOINT = os.environ['API_ENDPOINT']
# MEH_ENDPOINT = os.environ['MEH_ENDPOINT']
MEH_API_KEY = os.environ['MEH_API_KEY']  # Encrypted key
TOPIC_ARN = os.environ['TOPIC_ARN']
BUCKET_NAME = os.environ['BUCKET_NAME']

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


def decrypt_key(session, secret):
    return session.client('kms').decrypt(
        CiphertextBlob=b64decode(secret),
        EncryptionContext={
            'LambdaFunctionName': os.environ['AWS_LAMBDA_FUNCTION_NAME']
        }
    )['Plaintext'].decode('utf-8')


session = boto3.Session()

API_KEY = decrypt_key(session, MEH_API_KEY)

appsync = AppSync(API_ENDPOINT)
appsync.auth(session)


# -----------------------------------------------------------------------------
# Functions

# TODO: pass `appsync` instance so we can mock and test
def replace_current_deal(local, remote):
    """Archive `local` and update current deal with `remote`.

    Parameters
    ----------
    local : dict
        Deal `current_deal` fetched from AppSync
    remote : dict
        New deal fetched from meh.com API

    Returns
    -------
    [type]
        [description]

    Raises
    ------
    requests.exceptions.RequestException
        [description]
    AppSyncException
        [description]
    """
    # TODO: return tuple (bool, bool) respresenting success of (1.) and (2.)?

    # 1. Create copy of current_deal with `dealID` as `id`
    local['id'] = local['dealID']
    if local.get('launchStatus') != adequate.LaunchStatus.soldOut.name:
        local['launchStatus'] = adequate.LaunchStatus.expired.name
    local.pop('updatedAt', None)
    version = local.pop('_version', None)

    try:
        r1 = appsync.create_deal(local)
        r1.raise_for_errors()
    except RequestException as e:
        logger.exception(
            f'## Request to copy current_deal failed: {e.message}'
        )
        raise e
    except AppSyncException as e:
        try:
            handle_copy_error(local, e)
        except Exception as err:
            raise err

    # 2. Update current_deal with update
    # FIXME: this fails to overwrite any outdated fields not in `remote`
    # FIXME: update resolver so we don't have to handle `dealYear` / `monthDay`
    remote_id = remote['id']
    created_at = remote['createdAt']
    remote.update({'id': adequate.CURRENT_ID_KEY_VALUE,
                   'dealID': remote_id,
                   'dealYear': created_at[:4],
                   'monthDay': created_at[5:7] + created_at[8:10],
                   'soldOutAt': remote.get('soldOutAt'),
                   '_version': version})

    try:
        r2 = appsync.update_deal(remote)
        r2.raise_for_errors()
    except RequestException as e:
        logger.exception(
            f'## Request to replace current_deal failed: {e.message}'
        )
        raise e
    except AppSyncException as e:
        logger.exception(
            f'## Failed to replace current_deal: {e.message} - {e.errors}'
            f'\nDeal: {json.dumps(remote, indent=2)}'
        )
        raise e
    except BaseException as e:
        logger.exception(
            f'## Unexpected error while trying to replace curren_deal: {e}'
        )
        raise e
    return r2


# TODO: pass `appsync`, `session` instances so we can mock and test
# TODO: rather than call logger here, raise exception with message sent to logger
def handle_copy_error(deal, error):
    logger.error(
        f'## Failed to copy current_deal: {error.message} - {error.errors}'
        f'\nDeal: {json.dumps(deal, indent=2)}'
    )

    if error.errors and ('ConditionalCheckFailedException'
                         in ', '.join([e.error_type for e in error.errors])):
        # Check if deal has already been copied to database
        try:
            r = appsync.get_deal(deal['id'])
            r.raise_for_errors()
        except RequestException as e:
            logger.exception(
                f"## Unable to recover from error copying current_deal - "
                f"request to fetch Deal '{deal['id']}' failed: {e.message}"
            )
            raise e
        except AppSyncException as e:
            logger.exception(
                f"## Unable to recover from error copying current_deal - "
                f"encountered additional error fetching Deal '{deal['id']}':"
                f"{e.message} - {e.errors}"
            )
            raise e
        # except BaseException as e:

        # Check if copy of deal already exists ...
        existing = r.get('getDeal')
        if not existing:
            # TODO: improve message
            logger.exception(
                f"## Unable to recover from error copying current_deal; Deal"
                f"'{deal['id']} does not exist in db"
            )
            raise error

        # TODO: support passing selection set so we don't need to do this
        [existing.pop(k, None) for k in ['_version', 'topic', 'updatedAt']]

        if existing == deal:
            logger.info(
                f"## Skipping copy; deal '{deal['title']}' already exists in "
                f"db with id '{deal['id']}'"
            )
        else:
            # Copy of deal already exists but it does not match
            try:
                filepath = save_to_bucket(session, deal)
            except BaseException as e:
                logger.exception(
                    f"## Unable to recover from error copying current_deal - "
                    f"Deal'{deal['title']}' already exists in db with id "
                    f"'{deal['id']}' it but differs from current_deal. "
                    f"Encountered additional error trying to save Deal to S3: "
                    f"{e}"
                )
                raise error

            # TODO: use logger.warning instead?
            logger.error(
                f"## Unable to recover from error copying current_deal - "
                f"Deal'{deal['title']}' already exists in db with id "
                f"'{deal['id']}' but differs from current_deal. A copy was "
                f"saved to S3 at:'{filepath}'"
            )

    # Some other error we can't handle
    else:
        logger.exception(
            f"## Unable to recover from error copying current_deal"
        )
        raise error


def save_to_bucket(session, deal):
    """Save `deal` to AWS S3 and return path.

    Parameters
    ----------
    session : boto3.Session
        AWS boto3 Session
    deal : dict
        Deal to write to S3

    Returns
    -------
    str
        Path of created file

    Raises
    ------
    Exception
        Unable to save `deal` to S3
    """
    date_string = dt.utcnow().strftime("%Y-%m-%d-%H-%M")
    filename = f"copy_errors/{date_string}_{deal['id']}.json"

    response = session.client('s3').put_object(
        Bucket=BUCKET_NAME,
        Key=filename,
        Body=(bytes(json.dumps(deal).encode('UTF-8'))),
        ContentType='application/json'
    )
    # TODO: encapsulate this
    status_code = response.get('ResponseMetadata', {}).get('HTTPStatusCode')
    if status_code != 200:
        raise Exception(
            f"## Error writing to S3: {response['ResponseMetadata']}")

    return f'{BUCKET_NAME}/{filename}'


def send_sns(session, topic_arn, content):
    """Send message to SNS topic and return response.

    Parameters
    ----------
    session : boto3.Session
        Description
    topic_arn : None, optional
        ARN for destination SNS topic
    content : dict
        Message for SNS notification

        message_type : str
            SNS subject; must be one of ['new', 'delta']
        message : dict
            SNS message; structure varies depending on `subject`

    Returns
    -------
    dict
        Description
    """
    ALLOWED_MESSAGE_TYPES = [
        'new',
        'delta'
    ]

    ALLOWED_DELTA_TYPES = [
        'commentCount',
        'launchStatus'
    ]
    # TODO: use namedtuple for content?
    message_type = content['message_type']
    message = content['message']

    if message_type not in ALLOWED_MESSAGE_TYPES:
        raise ValueError(
            f"Invalid message_type - Received '{message_type}'. "
            f"Valid values are {ALLOWED_MESSAGE_TYPES}")

    # TODO: improve handling of Exception from missing message['delta_type']
    if message_type == 'delta':
        delta_type = message.get('delta_type')
        if delta_type not in ALLOWED_DELTA_TYPES:
            raise ValueError(
                f"Invalid delta_type - Received '{delta_type}'. "
                f"Valid values are {ALLOWED_DELTA_TYPES}")

    response = session.client('sns').publish(
        TopicArn=topic_arn,
        Subject=message_type,
        Message=json.dumps({'default': json.dumps(message)}),
        MessageStructure='json'
    )
    # TODO: encapsulate this
    status_code = response.get('ResponseMetadata', {}).get('HTTPStatusCode')
    if status_code != 200:
        raise Exception(
            f"## Error sending SNS: {response['ResponseMetadata']}")
    return response


# -----------------------------------------------------------------------------
# Lambda Handler

def lambda_handler(event, context):
    """AWS Lambda Function entrypoint to fetch deal from meh.com and update
    AppSync GraphQL API.

    Parameters
    ----------
    event: dict, required
        CloudWatch Scheduled event

        CloudWatch events doc: https://docs.aws.amazon.com/lambda/latest/dg/services-cloudwatchevents.html

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    dict
        DESCRIPTION
    """  # noqa E501
    global appsync
    global session

    # Fetch deal from meh.com and our API
    try:
        # Fetch / process remote deal
        update = adequate.meh(API_KEY)

        # Get current deal
        current_response = appsync.get_deal(adequate.CURRENT_ID_KEY_VALUE)
        current_response.raise_for_errors()

    # https://stackoverflow.com/a/16511493
    # TODO: handle `ValueError` from appsync
    except RequestException as e:
        logger.error(f'## Request to fetch deal failed: {e}')
        raise e
    except AppSyncException as e:
        logger.error(f'## Error: {e.message} - {e.errors}')
        raise e

    # Compare deals
    current = current_response.get('getDeal')
    if current is None:
        logger.info('## Current Deal Missing ...')

        update['id'] = adequate.CURRENT_ID_KEY_VALUE
        try:
            r = appsync.create_deal(update)
            r.raise_for_errors()
        except RequestException as e:
            logger.error(
                f'## Request to create current_deal failed: {e.message}'
            )
            raise e
        except AppSyncException as e:
            logger.error(
                f'## Failed to create current_deal: {e.message} - {e.errors}'
                f'\nDeal: {json.dumps(current, indent=2)}'
            )
            raise e

        # Notification
        # try:
        message = adequate.alert_message(update)
        # except ValueError as e:

    elif update['id'] == current.get('dealID'):
        logger.info('## Same Deal ...')

        delta = adequate.delta(current, update)
        if not delta:
            logger.info('## No changes to Deal')
            return
        else:
            logger.info(
                f"## Updating Deal '{current['title']}' with delta: '{delta}'"
            )

            try:
                r = appsync.update_deal(delta)
                r.raise_for_errors()
                # message = adequate.delta_message(delta)
            except RequestException as e:
                logger.error(
                    f'## Request to upate current_deal failed: {e.message}'
                )
                raise e
            except AppSyncException as e:
                logger.error(
                    f'## Failed to upate current_deal: {e.message} - '
                    f'{e.errors}\nDelta: {json.dumps(delta, indent=2)}'
                )
                raise e
            # except ValueError as e:

            # Notification
            # try:
            message = adequate.delta_message(update['id'], delta)
            # except ValueError as e:

            # Throttle `DealDelta.commentCount` notifications; we don't 
            # need to send one every 5 minutes
            # FIXME: implement better solution
            if message.get('delta_type') == 'commentCount':
                logger.info("Skipping commentCount update notification")
                return

    else:
        logger.info(
            f"## Replacing current_deal '{current['title']}' with "
            f"'{update['title']}'"
        )

        r = replace_current_deal(current, update)

        # Notification
        # try:
        message = adequate.alert_message(update)
        # except ValueError as e:
        #     logger.error(
        #         f"## Failed to generate notification: {e}"
        #         f"\nUpdate: {json.dumps(update, indent=2)}"
        #     )
        #     raise e

    # Send to Topic
    # logger.info('## Sending to SNS ...')
    try:
        sns_resp = send_sns(session, TOPIC_ARN, message)
    except Exception as e:
        logger.exception(f"## Failed to send SNS notification: {e}")
        raise e
