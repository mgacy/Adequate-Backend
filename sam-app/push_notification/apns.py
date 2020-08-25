"""
APNS Notification.

v 0.2
"""

import json
import boto3

# TODO: rename `ALLOWED_DELTA_TYPES`?
DELTA_TYPES = [
    'commentCount',
    'launchStatus'
]

ALLOWED_APNS_SERVERS = [
    'dev',
    'prod',
    'both'
]


class ResponseStatusError(Exception):
    """A boto3 request was not successful."""

    def __init__(self, status_code, response):
        # TODO: map different errors (400 - 499 / 500 - 599)?
        self.msg = f'Error: {status_code}'
        # TODO: extract `response['ResponseMetadata']`?
        self.response = response

    # def __repr__(self):


def make_delta_message(message):
    """Documentation

    Parameters
    ----------
    message : dict
        Message from SNS notification with subject of `delta`
    category : str
        APNS category

    Returns
    -------
    dict
        Message for APNS

    Raises
    ------
    KeyError
        Malformed `message`
    """
    try:
        deal_id = message['id']
        delta_type = message['delta_type']
        delta_value = message['delta_value']
    except KeyError as e:
        # TODO: is this preferable to the `KeyError` we're replacing?
        raise ValueError(f"Malformed delta - Missing key '{str(e)}'")
    else:
        if delta_type not in DELTA_TYPES:
            raise ValueError(
                f"Invalid `delta_type` - Received '{delta_type}'. "
                f"Valid values are {DELTA_TYPES}")

        apns_dict = _make_background_notification({
            'deal-id': deal_id,
            'adequate-delta-type': delta_type,
            'adequate-delta-value': delta_value})
        # TODO: add additional exception handling

        # To send APNS push messages via Boto3 you have to encode the json
        # twice. Once for the actual payload and once for the SNS message.
        # https://stackoverflow.com/a/20134162/4472195
        message = json.dumps(apns_dict, ensure_ascii=False)
        return message


def make_new_deal_message(message, apns_category):
    """Documentation

    Parameters
    ----------
    message : dict
        Message from SNS notification with subject of `new`

        id : str
            Deal's `dealID`
        title : str
            Deal's `title`
        price_string : str
            Price (or price range) for minimum purchase quantity of Deal
        deal_url : str
            Meh.com URL for Deal
        image_url : str
            URL for first image

    category : str
        APNS category

    Returns
    -------
    dict
        Message for APNS

    Raises
    ------
    KeyError
        Malformed `message`
    """
    TITLE_FORMAT = 'New Deal for {}'

    try:
        deal_id = message['id']
        deal_title = message['title']
        price_string = message['price_string']
        deal_url = message['deal_url']
        image_url = message['image_url']

    except KeyError as e:
        # TODO: is this preferable to the `KeyError` we're replacing?
        raise ValueError(f"Malformed message - Missing key '{str(e)}'")
    else:
        apns_dict = _make_notification(
            category=apns_category,
            title=TITLE_FORMAT.format(price_string),
            body=deal_title,
            content_available=True,
            mutable_content=True,
            additional={
                'deal-id': deal_id,
                'adequate-deal-url': deal_url,
                'adequate-image-url': image_url
            })

        # To send APNS push messages via Boto3 you have to encode the json
        # twice. Once for the actual payload and once for the SNS message.
        # https://stackoverflow.com/a/20134162/4472195
        message = json.dumps(apns_dict, ensure_ascii=False)
        return message


def publish_message(
    session, topic_arn, apns_server, apns_message,
    default_message='default message'
):
    """Publish APNS notification via SNS.

    Parameters
    ----------
    session : boto3.Session
        AWS boto3 Session
    topic_arn : str
        ARN  for destination SNS topic
    apns_server : str
        APNS server to use; allowed values: ['prod', 'dev', 'both']
    apns_message : str
        Message for SNS notification
    default : str, optional
        Message for `default` key

    Returns
    -------
    dict
        Response from AWS SNS

    Raises
    ------
    ValueError
        Invalid `apns_server` value
    """
    if apns_server not in ALLOWED_APNS_SERVERS:
        raise ValueError(
            f"Invalid `apns_server` - Received '{apns_server}'. "
            f"Valid values are {ALLOWED_APNS_SERVERS}")

    sns = session.client('sns')

    message = {
        'default': default_message
    }

    if apns_server in ['both', 'prod']:
        message['APNS'] = apns_message

    if apns_server in ['both', 'dev']:
        message['APNS_SANDBOX'] = apns_message

    return sns.publish(
        TopicArn=topic_arn,
        Message=json.dumps(message, ensure_ascii=False),
        MessageStructure='json'
    )


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
        raise ResponseStatusError(status_code, response)


# ----------------------------------------------------------------------------
# Make Message + Publish

# TODO: pass type encompassing region, topic, DealDelta, value?
def push_new_notification(
    session, topic_arn, apns_server, apns_category, message
):
    """Summary

    Parameters
    ----------
    session : boto3.Session
        AWS boto3 Session
    topic_arn : str
        AWS SNS Topic ARN
    apns_server : str
        APNS server to use; allowed values: ['prod', 'dev', 'both']
    apns_category : str
        APNS category
    message : dict
        Message from SNS notification with subject of `new`

    Returns
    -------
    dict
        Response from AWS SNS

    Raises
    ------
    ValueError
        Malformed `message` or invalid `apns_server` value
    """
    # Can raise ValueError
    message = make_new_deal_message(message, apns_category)
    # TODO: add additional exception handling
    response = publish_message(session, topic_arn, apns_server, message)
    # raise_for_status(response)
    return response


def push_delta_notification(session, topic_arn, apns_server, message):
    """Summary

    Parameters
    ----------
    session : boto3.Session
        AWS boto3 Session
    topic_arn : str
        AWS SNS Topic ARN
    apns_server : str
        APNS server to use; allowed values: ['prod', 'dev', 'both']
    message : dict
        Message from SNS notification with subject of `delta`

    Returns
    -------
    dict
        Response from AWS SNS

    Raises
    ------
    ValueError
        Malformed `message` or invalid `apns_server` value
    """
    # Can raise ValueError
    message = make_delta_message(message)
    # TODO: add additional exception handling
    response = publish_message(session, topic_arn, apns_server, message)
    # raise_for_status(response)
    return response


# ----------------------------------------------------------------------------
# Private

# TODO: rename `build_payload`?
def _make_notification(
    category, title, body=None, content_available=False, mutable_content=False,
    additional=None
):
    """Summary

    For full documentation of remote notifications, see:
    https://developer.apple.com/documentation/usernotifications/setting_up_a_remote_notification_server/generating_a_remote_notification

    Parameters
    ----------
    category : str
        APNS category
    title : str
        Notification title
    body : str, optional
        Notification body
    content_available : bool, optional
        If True, client will perform background app refresh
    mutable_content : bool, optional
        If True, client will pass notification to notification service app
        extension before delivery
    additional : dict, optional
        Additional, client-specific info

    Returns
    -------
    dict
        Description
    """  # noqa E501
    aps = {
        'category': category,
        'sound': 'bingbong.aiff'
    }

    # Alert
    if body:
        aps.update(alert={'title': title, 'body': body})
    else:
        aps.update(alert=title)

    # Mutable-Content
    if mutable_content:
        aps.update({'mutable-content': 1})

    # Content-Available
    if content_available:
        aps.update({'content-available': 1})

    apns_dict = {'aps': aps}

    # Client-specific info
    if additional:
        apns_dict.update(additional)

    return apns_dict


def _make_background_notification(additional=None):
    """Documentation

    Parameters
    ----------
    additional : dict, optional
        Additional, client-specific info

    Returns
    -------
    dict
        Description
    """
    apns_dict = {
        'aps': {
            'content-available': 1
        }
    }
    # Client-specific info
    if additional:
        apns_dict.update(additional)
    return apns_dict
