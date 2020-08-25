import requests
from .deal import CURRENT_ID_KEY_VALUE, delta
from .meh import _parse_response
from .models import LaunchStatus


MEH_ENDPOINT = 'https://api.meh.com/1/current.json'


# TODO: does this name really express its functionality? Rename deal?
def meh(api_key):
    """Return current deal from meh.com API with additional processing.

    Parameters
    ----------
    api_key : string
        API key for meh.com

    Returns
    -------
    dict
        Response

    Raises
    ------
    requests.exceptions.RequestException
        Description
    """
    params = {'apikey': api_key}
    r = requests.get(MEH_ENDPOINT, params=params)
    r.raise_for_status()
    return _parse_response(r.json())


def alert_message(deal):
    """Return message formatted for SNS.

    Parameters
    ----------
    deal : dict
        'deal' value from Meh.com API response

    Returns
    -------
    dict
        Payload for APNS notification

    Raises
    ------
    ValueError
        Malformed `deal`
    """
    # TODO: do I need to do any error handling here?

    try:
        deal_id = deal['dealID']
        deal_title = deal['title']
        deal_url = deal['url'] + '/checkout'
        image_url = deal['photos'][0]

        # Parse Prices
        min_quantity = deal.get('purchaseQuantity', {}).get('minimumLimit', 1)
        prices = [item['price'] for item in deal['items']]
    except KeyError as e:
        raise ValueError(f"Malformed deal - Missing key '{str(e)}'")

    # TODO: handle potential TypeError for `prices`?
    min_price = min(prices) * min_quantity * 0.1
    max_price = max(prices) * min_quantity * 0.1
    # TODO: verify prices are actually integers before specifying formatting?
    # TODO: do we need to convert to float?
    # TODO: simply send array of prices and let other lambda deal with formatting?
    if min_price < max_price:
        price_string = '${:.0f} - ${:.0f}'.format(min_price, max_price)
    else:
        price_string = '${:.0f}'.format(min_price)

    # TODO: return `namedtuple`?
    return {
        'message_type': 'new',
        'message': {
            'id': deal_id,
            'title': deal_title,
            'price_string': price_string,
            'deal_url': deal_url,
            'image_url': image_url
        }
    }


def delta_message(delta):
    try:
        deal_id = delta['id']
    except KeyError as e:
        raise ValueError(f"Malformed delta - Missing key '{str(e)}'")

    comment_count = delta.get('topic', {}).get('commentCount', None)
    launch_status = delta.get('launchStatus', None)

    # TODO: add support for `multiple`
    # For now, prioritize launchStatus
    if launch_status:
        # delta_type = DealDelta.launchStatus
        delta_type = 'launchStatus'
        delta_value = launch_status
    elif comment_count:
        # delta_type = DealDelta.commentCount
        delta_type = 'commentCount'
        delta_value = comment_count
    else:
        # TODO: is this the best way to handle?
        raise ValueError(" error")

    # TODO: return `namedtuple`?
    return {
        'message_type': 'delta',
        'message': {
            'id': deal_id,
            'delta_type': delta_type,
            'delta_value': delta_value
        }
    }


# TODO: add function to update deal.launchStatus
# This would eliminate the need for the following in the lambda:
# `launchStatus=deal.LaunchStatus.expired.name`
