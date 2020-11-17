import json
import logging
import os
import boto3
import apns

TOPIC_ARN = os.environ['TOPIC_ARN']
APNS_SERVER = os.environ['APNS_SERVER']
APNS_CATEGORY = os.environ['APNS_CATEGORY']

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
session = boto3.Session()


# ----------------------------------------------------------------------------
# Helpers

def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': str(err) if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
        }
    }


# ----------------------------------------------------------------------------
# Handler

def lambda_handler(event, context):
    """AWS Lambda Function entrypoint to send push notification for new or
    updated deal.

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """  # noqa E501

    global session

    logger.info(f'Received event: {json.dumps(event, indent=2)}')
    try:
        subject = event['Records'][0]['Sns']['Subject']
        # TODO: rename `body`?
        message = json.loads(event['Records'][0]['Sns']['Message'])
        # attributes = event['Records'][0]['Sns'].get('MessageAttributes', {})
    except ValueError as e:
        logger.error(f'## Unable to get notification attribute: {e}')
        raise e

    # TODO: I remember seeing AWS examples that used an attribute or something to do this
    if subject == 'new':
        logger.info(f"## New Deal: {message}")
        try:
            apns_message = apns.make_new_deal_message(message, APNS_CATEGORY)
        except (ValueError, KeyError) as e:
            logger.exception(f"## {e}")
            raise e

    elif subject == 'delta':
        logger.info(f"## Delta: {message}")
        apns_message = apns.make_delta_message(message)

    else:
        logger.error(f"## Invalid subject: '{subject}'")
        raise ValueError(f"Invalid subject: '{subject}'")

    logger.info("## Sending SNS message")
    try:
        response = apns.publish_message(session, TOPIC_ARN, APNS_SERVER,
                                        apns_message)
        apns.raise_for_status(response)
    except ValueError as e:
        logger.error(f"## {e}")
        raise e
    except apns.ResponseStatusError as e:
        logger.error(
            f"## Failed to send SNS message: {json.dumps(response, indent=2)}"
        )
        raise e
    else:
        return respond(None, response)
